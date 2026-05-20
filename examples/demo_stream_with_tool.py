"""v0.2 streaming + tool döngüsü — mock ile.

İki API çağrısı simüle edilir:
  1. Model "kelime kelime düşünüyor..." + tool_use bloğu (streaming)
  2. Model "final cevabı kelime kelime veriyor" (streaming, end_turn)

Gerçek hayatta bu olayları Anthropic SDK üretir. Burada biz simüle ediyoruz.
"""

import time
from agentlite import Agent, tool


# ─── ARAÇ ─────────────────────────────────────────────────────
@tool
def get_weather(city: str) -> str:
    """Bir şehrin güncel hava durumunu döndür."""
    return f"{city}: 22°C, güneşli"


# ─── MOCK ALT YAPISI ──────────────────────────────────────────
# Anthropic event'leri taklit eden minik yapı taşları.

class _AttrObj:
    """Dict-like obje — event.delta.text gibi attr erişimi için."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _MockStream:
    """'with client.messages.stream(...) as s:' içinde dönen şey.

    __iter__ ile event'leri sırayla verir.
    """
    def __init__(self, events):
        self._events = events

    def __iter__(self):
        for ev in self._events:
            time.sleep(0.05)   # gerçek streaming hissi için
            yield ev


class _MockStreamContext:
    """Context manager: with bloğu için."""
    def __init__(self, events):
        self._stream = _MockStream(events)
    def __enter__(self):
        return self._stream
    def __exit__(self, *args):
        pass


class MockClient:
    """İki turlu konuşmayı simüle eder."""
    def __init__(self):
        self.messages = self
        self.call_count = 0

    def stream(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            # 1. çağrı: model "düşünüyor" ve tool çağırıyor
            return _MockStreamContext([
                # Önce bir text bloğu (model konuşuyor)
                _AttrObj(type="content_block_start",
                         content_block=_AttrObj(type="text")),
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="text_delta", text="Hava ")),
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="text_delta", text="durumuna ")),
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="text_delta", text="bakayım.\n")),
                _AttrObj(type="content_block_stop"),
                # Sonra tool_use bloğu (input JSON parça parça gelir)
                _AttrObj(type="content_block_start",
                         content_block=_AttrObj(
                             type="tool_use", id="toolu_1",
                             name="get_weather"
                         )),
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="input_json_delta",
                                       partial_json='{"ci')),
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="input_json_delta",
                                       partial_json='ty":"Istan')),
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="input_json_delta",
                                       partial_json='bul"}')),
                _AttrObj(type="content_block_stop"),
                # Mesaj bitiş bilgisi
                _AttrObj(type="message_delta",
                         delta=_AttrObj(stop_reason="tool_use"),
                         usage=_AttrObj(input_tokens=100, output_tokens=30,
                                       cache_creation_input_tokens=0,
                                       cache_read_input_tokens=0)),
            ])

        # 2. çağrı: model artık tool sonucunu görüp final cevap üretiyor
        return _MockStreamContext([
            _AttrObj(type="content_block_start",
                     content_block=_AttrObj(type="text")),
            *[
                _AttrObj(type="content_block_delta",
                         delta=_AttrObj(type="text_delta", text=kelime + " "))
                for kelime in ["İstanbul'da", "hava", "22°C", "ve", "güneşli."]
            ],
            _AttrObj(type="content_block_stop"),
            _AttrObj(type="message_delta",
                     delta=_AttrObj(stop_reason="end_turn"),
                     usage=_AttrObj(input_tokens=50, output_tokens=15,
                                   cache_creation_input_tokens=0,
                                   cache_read_input_tokens=200)),
        ])


# ─── KULLANIM ─────────────────────────────────────────────────
if __name__ == "__main__":
    agent = Agent(
        model="claude-opus-4-7",
        system="Sen yardımcı bir hava durumu asistanısın.",
        tools=[get_weather],
        client=MockClient(),
    )

    print("=" * 60)
    print("👤 Kullanıcı: İstanbul'da hava nasıl?")
    print("=" * 60)
    print()

    for event in agent.stream("İstanbul'da hava nasıl?"):
        if event.type == "text":
            print(event.text, end="", flush=True)
        elif event.type == "tool_use":
            print(f"\n🔧 Tool: {event.name}({event.input})")
        elif event.type == "tool_result":
            print(f"   ← {event.result[:80]}")
        elif event.type == "done":
            print(f"\n\n[✅ bitti — {event.turn_count} tur]")
            print(f"   usage: {event.usage}")
        elif event.type == "error":
            print(f"\n❌ HATA: {event.message}")
