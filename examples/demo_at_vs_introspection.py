"""@ işareti ≠ introspection. İkisi BAŞKA şeyler."""


# ─── DECORATOR 1: @ var, introspection YOK ────────────────────
# Bu decorator fonksiyona dokunmadan geri verir. Pratikte yararsız ama
# meşru bir decorator — ve introspection hiç kullanılmıyor.

def hicbirsey_yapma(func):
    """Verilen fonksiyonu olduğu gibi geri ver."""
    return func   # ← burada hiçbir 'inspect' kullanılmıyor

@hicbirsey_yapma
def merhaba():
    print("Selam!")


# ─── DECORATOR 2: @ var, içinde introspection var ─────────────
import inspect

def parametreleri_say(func):
    """Fonksiyonun kaç parametresi olduğunu yazdır."""
    sig = inspect.signature(func)             # ← INTROSPECTION!
    print(f"  → '{func.__name__}' fonksiyonunun {len(sig.parameters)} parametresi var")
    return func

@parametreleri_say
def topla(a, b, c):
    return a + b + c


# ─── KULLANIM: @ İŞARETSİZ introspection ──────────────────────
# Bu da geçerli — decorator olmadan da introspection yapılabilir.

def selam(isim, yas):
    """Birini selamla."""
    return f"Selam {isim}"

print("\n=== @ kullanmadan introspection ===")
print(f"selam'ın adı: {selam.__name__}")           # introspection
print(f"selam'ın imzası: {inspect.signature(selam)}")  # introspection
