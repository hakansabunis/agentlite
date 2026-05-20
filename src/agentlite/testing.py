"""agentlite.testing — kullanıcılar için sahte (mock) client + yardımcılar.

Niçin public API?
Kullanıcı agent kodunu Anthropic API'ye gitmeden test edebilsin diye.
Gerçek API çağrısı 200ms+ + para; mock 0.5ms + bedava.

Kullanım:
    from agentlite.testing import MockClient, text_response, tool_use_response

    client = MockClient(responses=[
        tool_use_response("get_weather", {"city": "Istanbul"}),
        text_response("İstanbul'da hava 22°C."),
    ])
    agent = Agent(model="claude-opus-4-7", tools=[...], client=client)
    assert agent.run("hava?") == "İstanbul'da hava 22°C."

Tasarım: SCRIPTED — kullanıcı sırayla "bu çağrıda şunu döndür" der.
Factory fonksiyonlar (text_response vs.) Anthropic'in iç response
yapısını gizler, kullanıcı sadece dış API'yi görür.
"""

from __future__ import annotations

from typing import Any


# ─── Yapı taşları (kullanıcı bunlara dokunmaz, factory'ler kullanır) ──
# Anthropic SDK'sının response/event objelerini taklit eden minik sınıflar.
# .type ve diğer alanlara attribute olarak erişilebilsin.

class _Attrs:
    """Dict'i obje gibi expose et — event.delta.text gibi."""
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class _MockResponse:
    """Non-streaming response — client.messages.create() çağrılarında."""
    def __init__(self, content: list[Any], stop_reason: str,
                 usage: dict[str, int] | None = None):
        self.content = content
        self.stop_reason = stop_reason
        # Usage objesi opsiyonel — caching demosu için faydalı
        if usage is not None:
            self.usage = _Attrs(**usage)


class _MockStreamContext:
    """'with client.messages.stream(...) as s:' içindeki context manager."""
    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def __enter__(self) -> "_MockStreamContext":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def __iter__(self):
        yield from self._events


# ─── ANA MOCK CLIENT ─────────────────────────────────────────────
class MockClient:
    """Anthropic client'ının test için sahte versiyonu.

    İki tip senaryoyu destekler:
      - .create() çağrıları için 'responses' listesi
      - .stream() çağrıları için 'streams' listesi

    Her çağrıda sıradakini döndürür; tükenirse RuntimeError.
    """

    def __init__(
        self,
        responses: list[_MockResponse] | None = None,
        streams: list[list[Any]] | None = None,
    ) -> None:
        # Anthropic SDK'sında client.messages.create() formatı.
        # 'messages' alt-nesnesini biz olarak gösteriyoruz (self-reference).
        self.messages = self
        self._responses = list(responses or [])
        self._streams = list(streams or [])
        # Kaç çağrı yapıldı? Testte assertion için faydalı.
        self.create_call_count = 0
        self.stream_call_count = 0
        # Son çağrıda gönderilen kwargs (kullanıcı argümanları doğrulayabilsin)
        self.last_create_kwargs: dict[str, Any] = {}
        self.last_stream_kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> _MockResponse:
        if not self._responses:
            raise RuntimeError(
                "MockClient.create: response kuyruğu boş. "
                f"{self.create_call_count} çağrı yapıldı; sıradaki için "
                "'responses' listesine ekle."
            )
        self.create_call_count += 1
        self.last_create_kwargs = kwargs
        return self._responses.pop(0)

    def stream(self, **kwargs: Any) -> _MockStreamContext:
        if not self._streams:
            raise RuntimeError(
                "MockClient.stream: stream kuyruğu boş. "
                f"{self.stream_call_count} çağrı yapıldı; sıradaki için "
                "'streams' listesine ekle."
            )
        self.stream_call_count += 1
        self.last_stream_kwargs = kwargs
        return _MockStreamContext(self._streams.pop(0))


# ─── FACTORY'ler — kullanıcının yazacağı kısayollar ───────────────

def text_response(
    text: str,
    *,
    usage: dict[str, int] | None = None,
) -> _MockResponse:
    """Düz metin cevabı (end_turn). Tool yok.

    Örnek:
        text_response("Merhaba!")
        → response.content = [TextBlock("Merhaba!")]
        → response.stop_reason = "end_turn"
    """
    return _MockResponse(
        content=[_Attrs(type="text", text=text)],
        stop_reason="end_turn",
        usage=usage,
    )


def tool_use_response(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    text: str = "",
    tool_use_id: str = "toolu_test",
    usage: dict[str, int] | None = None,
) -> _MockResponse:
    """Tool çağırmak isteyen cevap (stop_reason='tool_use').

    Args:
        tool_name: çağrılacak tool adı
        tool_input: tool argümanları (dict)
        text: tool çağrısıyla beraber model'in opsiyonel metin çıktısı
        tool_use_id: tool_use bloğunun id'si (default: 'toolu_test')

    Örnek:
        tool_use_response("get_weather", {"city": "Istanbul"})
    """
    blocks = []
    if text:
        blocks.append(_Attrs(type="text", text=text))
    blocks.append(_Attrs(
        type="tool_use",
        id=tool_use_id,
        name=tool_name,
        input=tool_input,
    ))
    return _MockResponse(
        content=blocks,
        stop_reason="tool_use",
        usage=usage,
    )


def text_stream(
    text: str,
    *,
    chunk_size: int | None = None,
) -> list[Any]:
    """Düz metin için stream event listesi (end_turn).

    chunk_size belirtilirse metni o kadar karaktere böler;
    None ise kelime kelime böler.

    Örnek:
        text_stream("Merhaba dünya")
        → 'Merhaba ' ve 'dünya' kelimelerini ayrı event olarak verir
    """
    if chunk_size is None:
        # Kelime kelime
        parts = [w + " " for w in text.split()]
    else:
        parts = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    events = [_Attrs(type="content_block_start",
                     content_block=_Attrs(type="text"))]
    for p in parts:
        events.append(_Attrs(type="content_block_delta",
                             delta=_Attrs(type="text_delta", text=p)))
    events.append(_Attrs(type="content_block_stop"))
    events.append(_Attrs(
        type="message_delta",
        delta=_Attrs(stop_reason="end_turn"),
        usage=_Attrs(input_tokens=0, output_tokens=0,
                     cache_creation_input_tokens=0,
                     cache_read_input_tokens=0),
    ))
    return events


def tool_use_stream(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    text: str = "",
    tool_use_id: str = "toolu_test",
) -> list[Any]:
    """Streaming için tool_use senaryosu (stop_reason='tool_use').

    Tool input'unu JSON'a serialize edip parça parça yayınlar — gerçek
    Anthropic SDK'sının davranışını birebir taklit eder (Modül 3B dersi).
    """
    import json
    events = []

    # Önce opsiyonel text bloğu
    if text:
        events.append(_Attrs(type="content_block_start",
                             content_block=_Attrs(type="text")))
        events.append(_Attrs(type="content_block_delta",
                             delta=_Attrs(type="text_delta", text=text)))
        events.append(_Attrs(type="content_block_stop"))

    # Sonra tool_use bloğu — input'u parça parça akıt
    events.append(_Attrs(
        type="content_block_start",
        content_block=_Attrs(type="tool_use", id=tool_use_id, name=tool_name),
    ))
    # JSON'ı 3'er karakter parçalara böl — gerçek hayatta da böyle gelir
    json_str = json.dumps(tool_input)
    chunk_size = max(1, len(json_str) // 3 or 1)
    for i in range(0, len(json_str), chunk_size):
        events.append(_Attrs(
            type="content_block_delta",
            delta=_Attrs(type="input_json_delta",
                         partial_json=json_str[i:i + chunk_size]),
        ))
    events.append(_Attrs(type="content_block_stop"))

    # Mesaj kapanış
    events.append(_Attrs(
        type="message_delta",
        delta=_Attrs(stop_reason="tool_use"),
        usage=_Attrs(input_tokens=0, output_tokens=0,
                     cache_creation_input_tokens=0,
                     cache_read_input_tokens=0),
    ))
    return events


__all__ = [
    "MockClient",
    "text_response",
    "tool_use_response",
    "text_stream",
    "tool_use_stream",
]
