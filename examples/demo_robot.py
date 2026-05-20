"""Demo: Robot bir fonksiyonu nasıl 'inceler'?

Hayal et: bu fonksiyonu (get_weather) bir robota verdik.
Robot daha önce bunu hiç görmedi. Şimdi tek tek inceliyor.
"""

import inspect
from typing import get_type_hints


# ─── KULLANICI BUNU YAZDI ─────────────────────────────────────
def get_weather(city: str, days: int = 1) -> str:
    """Bir şehrin gelecek N günkü hava durumunu döndürür."""
    return f"{city}: hava güzel"


# ─── ROBOT ŞİMDİ İNCELİYOR ────────────────────────────────────
print("🤖 Robot: bana bir alet verildi, inceleyim...\n")

# 1. ADI NE?
print("Soru 1: Bu aletin adı ne?")
print(f"  Bakıyorum...  → '{get_weather.__name__}'")
print(f"  ✓ Adı 'get_weather'\n")

# 2. NE İŞE YARAR?
print("Soru 2: Ne işe yarar?")
print(f"  Üzerinde yazıyı arıyorum (docstring)...")
print(f"  → '{inspect.getdoc(get_weather)}'")
print(f"  ✓ Tamam, hava durumu aletiymiş\n")

# 3. NASIL KULLANILIR? (hangi argümanlar)
print("Soru 3: Bunu çalıştırmak için bana ne lazım?")
sig = inspect.signature(get_weather)
hints = get_type_hints(get_weather)
print(f"  İmzasını çıkardım: {sig}")
print(f"  Parametreler:")
for name, param in sig.parameters.items():
    tip = hints.get(name, "bilinmeyen")
    if param.default is inspect.Parameter.empty:
        zorunlu = "ZORUNLU"
    else:
        zorunlu = f"opsiyonel (varsayılan: {param.default})"
    print(f"    • '{name}' — tipi {tip.__name__}, {zorunlu}")

print("\n🤖 Robot: işte hepsi bu kadar! Şimdi bunu Anthropic API'ye anlatabilirim.")
