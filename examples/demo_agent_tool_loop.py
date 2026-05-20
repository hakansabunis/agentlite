"""Agent'ın tool döngüsü — mock ile.

İki API çağrısını taklit ediyoruz:
  1. Çağrı: model "get_weather aracını çağırmak istiyorum" diyor
  2. Çağrı: model "İstanbul'da hava 22°C" diye final cevap veriyor

Gerçek hayatta bu iki çağrıyı Claude yapardı. Burada biz simüle ediyoruz —
agent'ın MANTIĞINI test etmek için.
"""

from agentlite import Agent, tool


# ─── 1) Bir gerçek tool tanımla ───────────────────────────────
@tool
def get_weather(city: str) -> str:
    """Bir şehrin güncel hava durumunu döndürür."""
    return f"{city}: 22°C, güneşli"


# ─── 2) Mock response yapı taşları ────────────────────────────
class _Block:
    """Anthropic response.content içindeki bir bloğu taklit eder."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Response:
    """Tam bir API response objesi."""
    def __init__(self, content: list, stop_reason: str):
        self.content = content
        self.stop_reason = stop_reason


# ─── 3) MOCK CLIENT — iki turlu konuşmayı simüle eder ─────────
class MockClient:
    """İlk çağrıda tool_use, ikincide final text döndüren mock."""

    def __init__(self):
        self.messages = self
        self.call_count = 0   # kaçıncı çağrıda olduğumuzu izle

    def create(self, **kwargs):
        self.call_count += 1

        if self.call_count == 1:
            # 1. çağrı: model aracı çağırmak istiyor
            print(f"  📤 [mock] 1. çağrı: model 'get_weather' çağırıyor")
            return _Response(
                content=[
                    _Block(type="text", text="Hava durumuna bakayım."),
                    _Block(
                        type="tool_use",
                        id="toolu_abc123",
                        name="get_weather",
                        input={"city": "İstanbul"},
                    ),
                ],
                stop_reason="tool_use",
            )

        # 2. çağrı: model artık aracın sonucunu görüp final cevap veriyor
        print(f"  📤 [mock] 2. çağrı: model sonucu işledi, final cevap veriyor")
        # Bu çağrıda agent bize messages içinde tool_result'u verdi.
        # Mock olarak son user mesajını da gösterelim:
        son_mesaj = kwargs["messages"][-1]
        print(f"  📥 [mock] agent bize şunu gönderdi: {son_mesaj}")

        return _Response(
            content=[_Block(type="text", text="İstanbul'da hava 22°C ve güneşli.")],
            stop_reason="end_turn",
        )


# ─── 4) KULLANIM ──────────────────────────────────────────────
if __name__ == "__main__":
    agent = Agent(
        model="claude-opus-4-7",
        system="Sen yardımcı bir asistansın.",
        tools=[get_weather],
        client=MockClient(),
    )

    print("=" * 60)
    print("Kullanıcı: İstanbul'da hava nasıl?")
    print("=" * 60)

    final = agent.run("İstanbul'da hava nasıl?")

    print()
    print("=" * 60)
    print(f"🤖 Final cevap: {final}")
    print("=" * 60)
