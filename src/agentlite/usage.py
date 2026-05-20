"""agentlite.usage — token kullanımı + maliyet tahmini.

Modül 5 dersi: ölçemediğin şeyi iyileştiremezsin. Bu modül kullanıcının
agent'ının ne kadar token tükettiğini ve ne kadara mal olduğunu görmesini
sağlar.

Tasarım:
  - Usage: 4 token sayısı tutan immutable dataclass (frozen)
  - __add__ ile birikim (turlar arası toplam)
  - estimate_cost_usd(model): modele göre $ hesabı (cache fiyatları dahil)

Fiyatlar Anthropic'in 2026 listesi — değişebilir, _PRICING güncellenir.
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Fiyat tablosu (USD per 1M tokens) ────────────────────────
# Anthropic resmi fiyatları, 2026 sonu itibariyle.
# Cache hesabı standart kuralla yapılır:
#   - cache_creation: input fiyatının 1.25 katı
#   - cache_read:     input fiyatının 0.10 katı
_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7":   {"input":  5.00, "output": 25.00},
    "claude-opus-4-6":   {"input":  5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input":  3.00, "output": 15.00},
    "claude-sonnet-4-5": {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":  {"input":  1.00, "output":  5.00},
}

CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


@dataclass(frozen=True)
class Usage:
    """Bir veya daha fazla turun token kullanımı.

    Tüm alanlar 0'dan başlar; her API çağrısından sonra biriktirilir.
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def total_input(self) -> int:
        """Tüm input token'ları (cache dahil)."""
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    def total(self) -> int:
        """Tüm token'lar (input + output, cache dahil)."""
        return self.total_input() + self.output_tokens

    def __add__(self, other: "Usage") -> "Usage":
        """İki Usage'ı birleştir — turlar arası birikim için.

        Modül 3 hatırlat: tool döngüsünde her tur ayrı API çağrısı yapılır;
        kullanıcı toplam maliyeti görmek ister. + operatörü doğal.
        """
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=(
                self.cache_creation_input_tokens + other.cache_creation_input_tokens
            ),
            cache_read_input_tokens=(
                self.cache_read_input_tokens + other.cache_read_input_tokens
            ),
        )

    def estimate_cost_usd(self, model: str) -> float | None:
        """Modele göre $ tahmini. Bilinmeyen model için None.

        Hesap:
          input  ×  input_rate / 1M
        + output ×  output_rate / 1M
        + cache_write × input_rate × 1.25 / 1M
        + cache_read  × input_rate × 0.10 / 1M
        """
        rates = _PRICING.get(model)
        if rates is None:
            return None
        input_rate = rates["input"]
        output_rate = rates["output"]
        total_usd = (
            self.input_tokens * input_rate
            + self.output_tokens * output_rate
            + self.cache_creation_input_tokens * input_rate * CACHE_WRITE_MULTIPLIER
            + self.cache_read_input_tokens * input_rate * CACHE_READ_MULTIPLIER
        )
        return total_usd / 1_000_000

    @classmethod
    def from_api_object(cls, api_usage: object | None) -> "Usage":
        """Anthropic SDK'sının usage objesini Usage'a çevir.

        api_usage None ise veya alanlar eksikse, eksikleri 0 sayar.
        """
        if api_usage is None:
            return cls()
        return cls(
            input_tokens=int(getattr(api_usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(api_usage, "output_tokens", 0) or 0),
            cache_creation_input_tokens=int(
                getattr(api_usage, "cache_creation_input_tokens", 0) or 0
            ),
            cache_read_input_tokens=int(
                getattr(api_usage, "cache_read_input_tokens", 0) or 0
            ),
        )


__all__ = ["Usage"]
