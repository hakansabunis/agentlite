"""Streaming demo — kelime kelime cevap (mock ile)."""

import time
from agentlite import Agent


# ─── MOCK STREAMING CLIENT ────────────────────────────────────
# Anthropic'in 'with stream() as s:' yapısını taklit etmemiz lazım.
# Bunun için iki şey gerek:
#   1. Context manager — __enter__ ve __exit__ metotları
#   2. text_stream — bir generator

class _MockStream:
    """'with' bloğu içinde dönen nesne. text_stream attribute'una sahip."""

    def __init__(self, full_text: str, gecikme: float = 0.1):
        # Yapay olarak metni kelimelere böl, her kelimeyi sıraya koy.
        self._kelimeler = full_text.split()
        self._gecikme = gecikme

    @property
    def text_stream(self):
        """Generator — her kelimeyi (gecikme ile) tek tek verir."""
        for kelime in self._kelimeler:
            time.sleep(self._gecikme)
            yield kelime + " "


class _MockStreamContext:
    """'with client.messages.stream(...) as s:' içindeki context manager."""

    def __init__(self, full_text: str):
        self._stream = _MockStream(full_text)

    def __enter__(self):
        return self._stream    # 'as s' burada s'e yazılır

    def __exit__(self, *args):
        pass                   # cleanup gerekmez (gerçekte stream kapanır)


class MockClient:
    """Streaming destekli mock client."""

    def __init__(self):
        self.messages = self

    def stream(self, **kwargs):
        # Sahte bir cevap — kullanıcının sorusuna göre kabaca üret
        son_mesaj = kwargs["messages"][-1]["content"]
        sahte_cevap = (
            f"Merhaba! Sen şunu sordun: '{son_mesaj}'. "
            f"İşte sahte ama parça parça gelen cevabım."
        )
        return _MockStreamContext(sahte_cevap)


# ─── KULLANIM ─────────────────────────────────────────────────
if __name__ == "__main__":
    agent = Agent(
        model="claude-opus-4-7",
        system="",
        client=MockClient(),
    )

    print("Kullanıcı: Hava nasıl?")
    print("🤖 Agent: ", end="", flush=True)

    # for ile generator üzerinde dön — her parçayı anında bas.
    for parca in agent.stream_text("Hava nasıl?"):
        print(parca, end="", flush=True)

    print()   # son yeni satır
