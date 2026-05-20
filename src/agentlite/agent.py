"""Agent — Claude ile konuşan ana sınıf.

Bu modül kütüphanenin İKİNCİ ana parçası (tool.py'dan sonra).
Modül 3'teki query.ts'nin minyatür Python karşılığı.

v0.3 — STREAMING eklendi (stream_text metodu). Tool döngülü streaming sonra.
v0.2 — TOOL DÖNGÜSÜ eklendi. Artık gerçek bir agent: model araç çağırabilir,
       sonucu görüp yeniden düşünebilir.
"""

from __future__ import annotations

from typing import Any, Iterator

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
        client: Any = None,
    ) -> None:
        self.model = model
        self.system = system
        self.tools = tools or []
        self.max_turns = max_turns
        # Caching VARSAYILAN AÇIK — kullanıcı düşünmesin, doğru olan otomatik.
        # Modül 5 dersi: silent invalidator yapmadığımız sürece avantaj net.
        self.enable_caching = enable_caching

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
            raise RuntimeError(
                f"Beklenmeyen durdurma sebebi: {response.stop_reason}"
            )

        # max_turns aşıldı — güvenlik freni devreye girdi (Modül 3).
        raise RuntimeError(
            f"max_turns ({self.max_turns}) aşıldı. Döngü sonsuza gitmesin diye kesildi."
        )

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
