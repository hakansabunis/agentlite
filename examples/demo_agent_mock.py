"""Mock client ile Agent'ı test et — API anahtarı GEREKMEZ.

Bu, gerçek Claude'a gitmeden agent mantığını doğruladığımız test biçimi.
Mock client = Anthropic SDK'sını TAKLİT eden sahte nesne.
"""

from agentlite import Agent


# ─── MOCK (sahte) CLIENT ──────────────────────────────────────
# Anthropic'in client.messages.create(...) çağrısını taklit eder.
# Asıl Anthropic'i çağırmadan, kendi sahte cevabımızı döndürürüz.

class _MockBlock:
    """Anthropic response.content içindeki bir bloğu taklit eder."""
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _MockResponse:
    """Anthropic response objesini taklit eder."""
    def __init__(self, text: str):
        self.content = [_MockBlock(text)]
        self.stop_reason = "end_turn"


class _MockMessages:
    """client.messages alt-nesnesini taklit eder."""
    def create(self, **kwargs):
        # Gelen son mesajı al
        son_mesaj = kwargs["messages"][-1]["content"]
        # Sahte bir cevap üret
        sahte_cevap = f"[SAHTE CEVAP] Sen şunu sordun: '{son_mesaj}'"
        return _MockResponse(sahte_cevap)


class MockClient:
    """Anthropic.Anthropic() client'ını taklit eder."""
    def __init__(self):
        self.messages = _MockMessages()


# ─── KULLANIM ─────────────────────────────────────────────────
if __name__ == "__main__":
    # Mock client ile Agent yarat — API anahtarı gerekmiyor.
    agent = Agent(
        model="claude-opus-4-7",
        system="Sen yardımcı bir asistansın.",
        client=MockClient(),   # ← gerçek yerine sahte
    )

    cevap = agent.run("Bugün hava nasıl?")
    print(f"Agent cevabı: {cevap}")

    cevap2 = agent.run("İstanbul'da yaşam pahalı mı?")
    print(f"Agent cevabı: {cevap2}")
