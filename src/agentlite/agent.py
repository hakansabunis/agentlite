"""Agent — Claude ile konuşan ana sınıf.

Bu modül kütüphanenin İKİNCİ ana parçası (tool.py'dan sonra).
Modül 3'teki query.ts'nin minyatür Python karşılığı.

v0.2 — STREAM + TOOL döngüsü entegrasyonu (agent.stream metodu).
       Eski stream_text() korunuyor (sadece metin).
v0.1.0:
  - TOOL DÖNGÜSÜ: model araç çağırabilir, sonucu görüp yeniden düşünebilir.
  - PROMPT CACHING varsayılan açık.
  - PERMISSION SYSTEM (read_only, requires_confirmation).
"""

from __future__ import annotations

import json
from typing import Any, Iterator

from .errors import (
    AgentMaxTurnsError,
    UnexpectedStopReasonError,
)
from .events import (
    DoneEvent,
    ErrorEvent,
    StreamEvent,
    TextDeltaEvent,
    ToolResultEvent,
    ToolUseEvent,
)
from .tool import Tool


def _default_terminal_confirm(tool: Tool, args: dict[str, Any]) -> bool:
    """Varsayılan izin sorma — terminale 'y/N' sorar.

    Üretimde kullanıcı kendi confirm_fn'unu geçer (GUI, Slack, vb).
    """
    print(f"\n⚠️  Agent '{tool.name}' aracını çağırmak istiyor.")
    print(f"   Argümanlar: {args}")
    cevap = input("   İzin veriyor musun? [y/N]: ").strip().lower()
    return cevap in ("y", "yes", "evet", "e")


class Agent:
    """Bir Claude modeliyle konuşan agent (tool destekli).

    Kullanım:
        @tool
        def get_weather(city: str) -> str:
            '''Hava durumu döndür.'''
            return f"{city}: 22°C"

        agent = Agent(
            model="claude-opus-4-7",
            system="Sen bir asistansın.",
            tools=[get_weather],
        )
        agent.run("İstanbul'da hava nasıl?")
    """

    def __init__(
        self,
        model: str,
        system: str = "",
        tools: list[Tool] | None = None,
        max_turns: int = 10,
        enable_caching: bool = True,
        confirm_fn: Any = None,
        tool_choice: str | dict[str, Any] | None = None,
        client: Any = None,
    ) -> None:
        self.model = model
        self.system = system
        self.tools = tools or []
        self.max_turns = max_turns
        # Caching VARSAYILAN AÇIK — kullanıcı düşünmesin, doğru olan otomatik.
        # Modül 5 dersi: silent invalidator yapmadığımız sürece avantaj net.
        self.enable_caching = enable_caching
        # Tool kullanım kısıtı — Anthropic'in 4 modu (auto/any/tool/none).
        # __init__'te belirtilirse her run/stream'de bu kullanılır;
        # run()/stream() çağrısında override edilebilir.
        self.default_tool_choice = tool_choice

        # İSİM → TOOL eşlemesi — döngü sırasında "get_weather" gelince
        # hangi Tool olduğunu HIZLI bulmak için.
        self._tool_by_name: dict[str, Tool] = {t.name: t for t in self.tools}

        # ── İzin sorma fonksiyonu (Modül 4) ──
        # Kullanıcı verirse onu kullan; vermezse terminal tabanlı varsayılan.
        # Bu sayede testte sahte (hep evet/hep hayır) verebiliriz; üretimde
        # GUI/Slack/web UI fonksiyonu geçilebilir. Dependency injection ruhu.
        self.confirm_fn = confirm_fn or _default_terminal_confirm

        # Dependency injection — client dışarıdan verilebilir (test için).
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client

    # ──────────────────────────────────────────────────────────────
    # STREAM + TOOL DÖNGÜSÜ — v0.2'nin yıldız özelliği
    #
    # Modül 3 (query loop) + Modül 8 (stream events) birleşimi.
    # Anthropic SDK'nın stream event'lerini bizim StreamEvent'lere çevirip
    # tool döngüsünü canlı yönetir. Kullanıcı için tek bir akış.
    # ──────────────────────────────────────────────────────────────
    def stream(self, user_message: str) -> Iterator[StreamEvent]:
        """Agent'ı bir kullanıcı mesajıyla çalıştır, EVENT akışı üret.

        Yield edilen tipler:
            TextDeltaEvent   — modelin yeni metin parçası
            ToolUseEvent     — model tool çağırmak istiyor (input tamam)
            ToolResultEvent  — bir tool çalıştı (veya reddedildi)
            DoneEvent        — agent bitti (final metin + usage)
            ErrorEvent       — hata (max_turns aşıldı vs.)

        Kullanım:
            for event in agent.stream("..."):
                if event.type == "text":
                    print(event.text, end="", flush=True)
                elif event.type == "tool_use":
                    print(f"🔧 {event.name}({event.input})")
                ...
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        for turn in range(1, self.max_turns + 1):
            # ── 1) Bir stream aç ve event'leri TOPLA ──
            # Anthropic SDK'sının stream'inden gelen ham event'leri
            # bizim event tiplerimize dönüştürürken AYNI ZAMANDA
            # assistant mesajını yeniden inşa ediyoruz (sonra geri yollamak için).
            assistant_blocks: list[dict[str, Any]] = []
            current_block: dict[str, Any] | None = None  # şu an inşa edilen blok
            partial_json = ""  # tool_use input için biriken JSON parçaları
            stop_reason: str | None = None
            usage: dict[str, int] = {}

            with self._open_stream(messages) as stream:
                for raw_event in stream:
                    et = raw_event.type

                    # Yeni blok başladı (text veya tool_use)
                    if et == "content_block_start":
                        cb = raw_event.content_block
                        if cb.type == "text":
                            current_block = {"type": "text", "text": ""}
                        elif cb.type == "tool_use":
                            current_block = {
                                "type": "tool_use",
                                "id": cb.id,
                                "name": cb.name,
                                "input": {},
                            }
                            partial_json = ""   # bu blok için sıfırla

                    # Blok içine parça geldi
                    elif et == "content_block_delta":
                        delta = raw_event.delta
                        if delta.type == "text_delta" and current_block is not None:
                            current_block["text"] += delta.text
                            yield TextDeltaEvent(text=delta.text)  # ← CANLI akıt
                        elif delta.type == "input_json_delta":
                            # Tool input'u parça parça JSON metin halinde gelir.
                            # Biriktir, blok bittiğinde parse et.
                            partial_json += delta.partial_json

                    # Blok bitti — finalize et
                    elif et == "content_block_stop":
                        if current_block is None:
                            continue
                        if current_block["type"] == "tool_use":
                            # JSON'u parse et (boş ise {})
                            try:
                                current_block["input"] = (
                                    json.loads(partial_json) if partial_json else {}
                                )
                            except json.JSONDecodeError:
                                current_block["input"] = {}
                            # Şimdi tool_use eventi yield et — input ARTIK tamam
                            yield ToolUseEvent(
                                name=current_block["name"],
                                input=current_block["input"],
                                tool_use_id=current_block["id"],
                            )
                        assistant_blocks.append(current_block)
                        current_block = None
                        partial_json = ""

                    # Mesaj kapanış meta-bilgisi (stop_reason + usage)
                    elif et == "message_delta":
                        if hasattr(raw_event, "delta") and hasattr(raw_event.delta, "stop_reason"):
                            stop_reason = raw_event.delta.stop_reason
                        if hasattr(raw_event, "usage"):
                            u = raw_event.usage
                            # Sadece olan alanları topla — birikimli
                            for k in ("input_tokens", "output_tokens",
                                      "cache_creation_input_tokens",
                                      "cache_read_input_tokens"):
                                v = getattr(u, k, None)
                                if v is not None:
                                    usage[k] = usage.get(k, 0) + v

            # ── 2) Stream kapandı. Şimdi karar zamanı: bitti mi, tool mu? ──
            if stop_reason == "end_turn":
                # Toplam metin = tüm text bloklarının birleşimi
                final_text = "".join(
                    b["text"] for b in assistant_blocks if b["type"] == "text"
                )
                yield DoneEvent(final_text=final_text, turn_count=turn, usage=usage)
                return

            if stop_reason == "tool_use":
                # ── 3) Assistant mesajını messages'a ekle ──
                messages.append({
                    "role": "assistant",
                    "content": [self._block_to_dict_v2(b) for b in assistant_blocks],
                })

                # ── 4) Tool'ları çalıştır, sonuçları topla ──
                tool_results = []
                for block in assistant_blocks:
                    if block["type"] != "tool_use":
                        continue
                    result_text, is_error = self._execute_tool(block)
                    yield ToolResultEvent(
                        tool_use_id=block["id"],
                        result=result_text,
                        is_error=is_error,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result_text,
                        "is_error": is_error,
                    })

                # ── 5) Sonuçları user mesajı olarak ekle, döngüye devam ──
                messages.append({"role": "user", "content": tool_results})
                continue

            # Beklenmeyen stop_reason — ErrorEvent ile yield (raise değil)
            yield ErrorEvent(message=str(UnexpectedStopReasonError(stop_reason)))
            return

        # max_turns aşıldı
        yield ErrorEvent(message=str(AgentMaxTurnsError(self.max_turns)))

    # ──────────────────────────────────────────────────────────────
    # STREAMING — kelime kelime cevap (basit versiyon, tool yok)
    # ──────────────────────────────────────────────────────────────
    def stream_text(self, user_message: str) -> Iterator[str]:
        """Modelin cevabını PARÇA PARÇA üret (generator).

        Kullanım:
            for parca in agent.stream_text("Merhaba"):
                print(parca, end="", flush=True)

        NOT: bu basit versiyon SADECE text döndürür. Streaming + tool döngüsü
        karmaşık bir konu — sonra eklenecek (Ders 2C-ileri).

        İade tipi 'Iterator[str]' — yani üzerinde for ile dönülebilen bir
        metin akışı. Her 'yield' çağıranı tek bir parça verir.
        """
        messages = [{"role": "user", "content": user_message}]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if self.system:
            kwargs["system"] = self.system

        # client.messages.stream(...) bir CONTEXT MANAGER döndürür.
        # 'with' bloğu sayesinde stream bitince otomatik kapatılır.
        with self.client.messages.stream(**kwargs) as stream:
            for text_delta in stream.text_stream:
                yield text_delta   # ← her parçayı çağırana akıt

    # ──────────────────────────────────────────────────────────────
    # ANA DÖNGÜ — kütüphanenin kalbi
    # Modül 3'teki query.ts'nin minyatür halini burada görüyorsun.
    # ──────────────────────────────────────────────────────────────
    def run(self, user_message: str) -> str:
        """Bir kullanıcı mesajı al, agent döngüsünü çalıştır, FINAL metni döndür.

        Akış (Modül 3 ile birebir aynı):
          1. Mesajı modele gönder
          2. Cevap geldi mi?
             - "end_turn"  → çık, metni döndür
             - "tool_use"  → araçları ÇALIŞTIR, sonuçları ekle, BAŞA DÖN
             - diğeri      → hata fırlat
          3. max_turns güvenlik freni — sonsuz döngüye karşı
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        for turn in range(1, self.max_turns + 1):
            # ── 1) Modele sor ──
            response = self._call_claude(messages)

            # ── 2) Stop reason'a göre dallan ──
            if response.stop_reason == "end_turn":
                # Model "bitti" dedi. Son metin bloğunu döndür.
                return self._extract_final_text(response)

            if response.stop_reason == "tool_use":
                # Model araç istiyor. Çalıştır, sonuçları MESSAGES'a ekle.
                messages = self._handle_tool_use(response, messages)
                continue   # ← döngü başa dön, yeni cevap iste

            # Bilinmeyen / hata durumları (refusal, max_tokens vs.)
            raise UnexpectedStopReasonError(response.stop_reason)

        # max_turns aşıldı — güvenlik freni devreye girdi (Modül 3).
        raise AgentMaxTurnsError(self.max_turns)

    # ──────────────────────────────────────────────────────────────
    # YARDIMCI METOTLAR (alt çizgi → dahili, kullanıcıya açık değil)
    # ──────────────────────────────────────────────────────────────
    def _call_claude(self, messages: list[dict[str, Any]]) -> Any:
        """Tek bir API çağrısı yap, response döndür.

        Modül 5 dersi: caching açıksa system promptunu cache_control ile sar.
        Render sırası 'tools → system → messages' olduğu için, system'in son
        bloğuna cache_control koymak HEM tools'u HEM system'i birlikte cache'ler.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }

        # ── System promptu — caching'e göre iki farklı format ──
        if self.system:
            if self.enable_caching:
                # CACHE'Lİ FORMAT: liste içinde dict, son blokta cache_control.
                # Bu format API'ye "buraya kadarki her şeyi (tools + system) cache'le" der.
                kwargs["system"] = [{
                    "type": "text",
                    "text": self.system,
                    "cache_control": {"type": "ephemeral"},
                }]
            else:
                # Düz string — cache yok.
                kwargs["system"] = self.system

        # ── Araçlar — varsa Anthropic formatında gönder ──
        if self.tools:
            kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in self.tools
            ]
            # tool_choice (varsa) — Anthropic API formatına çevrilmiş
            tc = self._resolve_tool_choice(None)
            if tc is not None:
                kwargs["tool_choice"] = tc

        return self.client.messages.create(**kwargs)

    def _handle_tool_use(
        self,
        response: Any,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Modelin tool_use bloklarını çalıştır, sonuçları messages'a ekle.

        Önemli: GELEN TÜM cevabı (text + tool_use) assistant mesajı olarak
        sakla — modelin düşünce zincirini bozmasın. Sonra sonuçları TEK
        bir user mesajında topla.
        """
        # 1) Modelin tüm cevabını assistant olarak ekle.
        messages.append({
            "role": "assistant",
            "content": [self._block_to_dict(b) for b in response.content],
        })

        # 2) Her tool_use bloğunu çalıştır, sonuçları topla.
        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool = self._tool_by_name.get(block.name)
            if tool is None:
                result = f"HATA: '{block.name}' adında bir araç yok"
                is_error = True
            else:
                # ── İZİN KONTROLÜ (Modül 4 dersi) ──
                # read_only=True → her zaman izin ver, sorma
                # requires_confirmation=True ve read_only değil → kullanıcıya sor
                # Diğer durumlar → otomatik izin
                allowed = self._check_permission(tool, block.input)
                if not allowed:
                    result = f"İZİN REDDEDİLDİ: kullanıcı '{tool.name}' çağrısını onaylamadı"
                    is_error = True
                else:
                    try:
                        result = str(tool.call(**block.input))
                        is_error = False
                    except Exception as e:
                        result = f"HATA: araç çalışırken patladı → {e}"
                        is_error = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,    # ZORUNLU — eşleştirme için
                "content": result,
                "is_error": is_error,
            })

        # 3) Sonuçları TEK user mesajı olarak ekle (Modül 6 dersi: paralel
        # araç çağrıları varsa hepsi tek mesajda gönderilir, ayrı ayrı değil).
        messages.append({"role": "user", "content": tool_results})

        return messages

    def _check_permission(self, tool: Tool, args: dict[str, Any]) -> bool:
        """Bu tool çağrısı bu argümanlarla yapılabilir mi?

        Modül 4'teki izin akışının minik versiyonu:
          1. read_only → her zaman izinli (zararsız)
          2. requires_confirmation → kullanıcıya sor
          3. Diğer → otomatik izin
        """
        # Salt-okunur araç zararsız sayılır — soruya zaman harcama.
        if tool.read_only:
            return True

        # Onay gereken araç → confirm_fn'a sor.
        if tool.requires_confirmation:
            return bool(self.confirm_fn(tool, args))

        # Hiçbir bayrak yoksa varsayılan: izin ver.
        return True

    def _resolve_tool_choice(
        self, override: str | dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """tool_choice string'ini Anthropic API formatına çevir.

        Kabul edilen girdiler:
            None / "auto"     → None (varsayılan davranış; API'ye gönderilmez)
            "any"             → {"type": "any"}
            "none"            → {"type": "none"}
            "<tool-name>"     → {"type": "tool", "name": "<tool-name>"}
            dict              → olduğu gibi (geriye dönük uyumluluk)

        Bilinmeyen string → kullanıcının kendi tool'unun adı varsayılır;
        ama o ad mevcut tool'larda yoksa erken hata fırlatırız (fail-fast).
        """
        choice = override if override is not None else self.default_tool_choice
        if choice is None or choice == "auto":
            return None
        if isinstance(choice, dict):
            return choice
        if choice == "any":
            return {"type": "any"}
        if choice == "none":
            return {"type": "none"}
        # Tool adı varsayımı
        if choice not in self._tool_by_name:
            raise ValueError(
                f"tool_choice {choice!r}: bu adda bir tool yok. "
                f"Mevcut tool'lar: {list(self._tool_by_name.keys())}"
            )
        return {"type": "tool", "name": choice}

    # ── stream() için yardımcılar ─────────────────────────────────
    def _open_stream(self, messages: list[dict[str, Any]]) -> Any:
        """client.messages.stream(...) için kwargs'ları hazırlar.

        _call_claude ile aynı mantık ama .stream() döndürür.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if self.system:
            if self.enable_caching:
                kwargs["system"] = [{
                    "type": "text", "text": self.system,
                    "cache_control": {"type": "ephemeral"},
                }]
            else:
                kwargs["system"] = self.system

        if self.tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description,
                 "input_schema": t.input_schema}
                for t in self.tools
            ]
            tc = self._resolve_tool_choice(None)
            if tc is not None:
                kwargs["tool_choice"] = tc

        return self.client.messages.stream(**kwargs)

    def _execute_tool(self, block: dict[str, Any]) -> tuple[str, bool]:
        """Bir tool_use bloğunu çalıştır → (result, is_error) döndür.

        İzin kontrolü ve hata yakalama dahil. stream() ve run()'da paylaşılan
        mantığı tek yere topladık (DRY — kursumuzun Modül 2 dersi:
        sorumluluğu doğru yere koy).
        """
        tool = self._tool_by_name.get(block["name"])
        if tool is None:
            return f"HATA: '{block['name']}' adında bir araç yok", True

        if not self._check_permission(tool, block["input"]):
            return (
                f"İZİN REDDEDİLDİ: kullanıcı '{tool.name}' çağrısını onaylamadı",
                True,
            )

        try:
            return str(tool.call(**block["input"])), False
        except Exception as e:  # noqa: BLE001
            return f"HATA: araç çalışırken patladı → {e}", True

    def _block_to_dict_v2(self, block: dict[str, Any]) -> dict[str, Any]:
        """stream() içinde bloklarımız zaten dict olarak inşa ediliyor,
        sadece messages'a uygun forma çevir."""
        if block["type"] == "text":
            return {"type": "text", "text": block["text"]}
        if block["type"] == "tool_use":
            return {
                "type": "tool_use",
                "id": block["id"],
                "name": block["name"],
                "input": block["input"],
            }
        raise ValueError(f"Bilinmeyen blok tipi: {block['type']}")

    def _block_to_dict(self, block: Any) -> dict[str, Any]:
        """Anthropic response bloğunu API'ye geri gönderilebilir dict'e çevir."""
        if block.type == "text":
            return {"type": "text", "text": block.text}
        if block.type == "tool_use":
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            }
        # Diğer tipleri (thinking vs.) ileride ekleyebiliriz.
        raise ValueError(f"Bilinmeyen blok tipi: {block.type}")

    def _extract_final_text(self, response: Any) -> str:
        """Response'tan en son text bloğunu al ve döndür."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
