"""Demo 2: Decorator — fonksiyonu sarmalama ve dönüştürme."""

# ─── ÖRNEK 1: Sıradan decorator (fonksiyon → fonksiyon) ───────────
# Klasik kullanım: orijinal fonksiyonu sarmalayıp davranışını ekle.

def loglayan(func):
    """Bir fonksiyonu sarmalar — çağrıldığında loglar."""
    def wrapper(*args, **kwargs):
        print(f"[LOG] {func.__name__} çağrıldı: args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"[LOG] {func.__name__} döndü: {result}")
        return result
    return wrapper


# @loglayan TAM OLARAK şuna eşdeğer:
#   def topla(a, b): ...
#   topla = loglayan(topla)
@loglayan
def topla(a: int, b: int) -> int:
    return a + b


print("=== Örnek 1: Sarmalayıcı decorator ===")
sonuc = topla(2, 3)
print(f"Final: {sonuc}\n")


# ─── ÖRNEK 2: Tip dönüştüren decorator (fonksiyon → BAŞKA tip nesne) ───
# Bizim @tool'umuz BU kategoride. Fonksiyon GİRİYOR, bambaşka bir nesne ÇIKIYOR.

from dataclasses import dataclass

@dataclass
class FunctionInfo:
    """Bir fonksiyonun meta bilgilerini tutan kapsayıcı."""
    name: str
    arg_count: int

def bilgi_topla(func):
    """Fonksiyonu alır, FunctionInfo nesnesine çevirir."""
    import inspect
    sig = inspect.signature(func)
    return FunctionInfo(
        name=func.__name__,
        arg_count=len(sig.parameters),
    )


@bilgi_topla
def hesapla(x: int, y: int, z: int) -> int:
    """3 sayı toplar."""
    return x + y + z


print("=== Örnek 2: Tip dönüştüren decorator ===")
print(f"hesapla TİPİ artık fonksiyon değil: {type(hesapla).__name__}")
print(f"İçinde ne var: {hesapla}")
print(f"hesapla.name = {hesapla.name}")
print(f"hesapla.arg_count = {hesapla.arg_count}")

# Şimdi hesapla'yı çağırmaya çalış — HATA verecek!
try:
    hesapla(1, 2, 3)
except TypeError as e:
    print(f"\nÇağırınca hata: {e}")
    print("→ Çünkü hesapla artık fonksiyon değil, FunctionInfo nesnesi.")
