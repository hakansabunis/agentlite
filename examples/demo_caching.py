"""Prompt caching — mock ile usage istatistiklerini gözlemle."""

from agentlite import Agent


# ─── MOCK — cache davranışını taklit eden client ──────────────
class _Usage:
    def __init__(self, input_tokens, cache_creation, cache_read, output_tokens):
        self.input_tokens = input_tokens
        self.cache_creation_input_tokens = cache_creation
        self.cache_read_input_tokens = cache_read
        self.output_tokens = output_tokens


class _Block:
    type = "text"
    def __init__(self, text):
        self.text = text


class _Response:
    def __init__(self, text, usage):
        self.content = [_Block(text)]
        self.stop_reason = "end_turn"
        self.usage = usage


class MockClient:
    """İlk çağrıda cache YAZAR, sonrakilerde OKUR."""

    def __init__(self):
        self.messages = self
        self.gorulen_prefix: str | None = None

    def create(self, **kwargs):
        # Sistemin önbellek prefix'i — gerçek API hash hesaplar, biz string karşılaştırıyoruz.
        prefix = repr(kwargs.get("system", "")) + repr(kwargs.get("tools", []))

        if self.gorulen_prefix == prefix:
            # Aynı prefix → CACHE HIT
            usage = _Usage(
                input_tokens=50,                  # sadece yeni mesaj
                cache_creation=0,
                cache_read=10_000,                # önbellekten okundu
                output_tokens=100,
            )
            print("  📊 [mock] CACHE HIT — büyük tasarruf!")
        else:
            # Farklı prefix → CACHE WRITE (ilk seferdeki gibi)
            self.gorulen_prefix = prefix
            usage = _Usage(
                input_tokens=50,
                cache_creation=10_000,            # önbelleğe yazıldı
                cache_read=0,
                output_tokens=100,
            )
            print("  📊 [mock] CACHE WRITE — ilk kez gördüm bu sistemi")

        return _Response(text="(sahte cevap)", usage=usage)


# ─── DEMO ─────────────────────────────────────────────────────
def maliyet_yazdir(response):
    u = response.usage
    print(f"     input          = {u.input_tokens}")
    print(f"     cache_creation = {u.cache_creation_input_tokens}")
    print(f"     cache_read     = {u.cache_read_input_tokens}")
    print(f"     output         = {u.output_tokens}")


if __name__ == "__main__":
    client = MockClient()
    agent = Agent(
        model="claude-opus-4-7",
        system="Sen büyük bir müşteri destek asistanısın. " * 1000,  # uzun sistem
        client=client,
        enable_caching=True,    # ← cache'i AÇ
    )

    # 3 ardışık istek — caching açık olduğu için 2. ve 3. CACHE HIT olmalı.
    print("\n=== 1. ISTEK (cache yazılacak) ===")
    agent.run("Merhaba, sorum var.")
    son = client.create_son_response if hasattr(client, 'create_son_response') else None

    # Her isteği tekrar manuel yapalım, response'u görmek için:
    print("\n--- direkt API'yi izleyerek ---")
    for i in range(1, 4):
        print(f"\nİstek #{i}:")
        response = client.create(
            model="claude-opus-4-7",
            system=[{"type": "text", "text": "Aynı sistem promptu", "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Soru {i}"}],
        )
        maliyet_yazdir(response)


    print("\n=== TASARRUF ÖZETİ ===")
    print("İlk istek: 10.000 token cache'e YAZILDI (1.25× fiyat)")
    print("Sonraki 2 istek: her biri 10.000 token cache'ten OKUNDU (0.1× fiyat)")
    print()
    print("Naif yol:    3 × 10.000 = 30.000 token tam fiyatla")
    print("Cache yolu:  10.000 (yaz, 1.25×) + 2 × 10.000 (oku, 0.1×) = ~14.500 token eşdeğeri")
    print("Tasarruf:    ~%52 (3 istekte; istek sayısı arttıkça oran %88'e yaklaşır)")
