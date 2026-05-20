"""Streaming gerçekten parça parça mı geliyor? Zaman damgalı kanıt."""

import time
from agentlite import Agent


class _MockStream:
    def __init__(self, text: str):
        self._kelimeler = text.split()

    @property
    def text_stream(self):
        for kelime in self._kelimeler:
            time.sleep(0.3)   # her kelime arasında 0.3 saniye
            yield kelime + " "


class _MockStreamContext:
    def __init__(self, text):
        self._s = _MockStream(text)
    def __enter__(self): return self._s
    def __exit__(self, *args): pass


class MockClient:
    messages = property(lambda self: self)
    def stream(self, **kw):
        return _MockStreamContext("Merhaba bu parça parça gelen bir cevap")


if __name__ == "__main__":
    agent = Agent(model="x", client=MockClient())

    baslangic = time.time()
    print(f"[t=0.0s]  Başladık")

    for parca in agent.stream_text("test"):
        gecen = time.time() - baslangic
        print(f"[t={gecen:.1f}s]  Geldi: '{parca.strip()}'")

    print(f"[t={time.time()-baslangic:.1f}s]  Bitti")
