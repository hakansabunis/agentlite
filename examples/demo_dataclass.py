"""Demo 3: Dataclass + frozen=True."""

# ─── ÖRNEK 1: ESKİ YOL — el ile yazılmış sınıf ─────────────────
# Sadece "name + age tutan bir nesne" için bu kadar şey gerek:

class KisiEski:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"KisiEski(name={self.name!r}, age={self.age!r})"

    def __eq__(self, other):
        if not isinstance(other, KisiEski):
            return False
        return self.name == other.name and self.age == other.age


# ─── ÖRNEK 2: YENI YOL — @dataclass ile ────────────────────────
# Aynı şey, 4 satır:

from dataclasses import dataclass

@dataclass
class KisiYeni:
    name: str
    age: int


# Test edelim — ikisi de aynı işi yapar:
print("=== Eski vs Yeni — aynı davranış ===")
a = KisiEski("Ali", 30)
b = KisiYeni("Ali", 30)

print(f"Eski:  {a}")
print(f"Yeni:  {b}")

# Eşitlik kontrolü
print(f"\nEski a == KisiEski('Ali', 30) → {a == KisiEski('Ali', 30)}")
print(f"Yeni b == KisiYeni('Ali', 30) → {b == KisiYeni('Ali', 30)}")


# ─── ÖRNEK 3: frozen=True — değişmez (immutable) ───────────────
# Dataclass'a frozen=True dersek, oluşturduktan SONRA değiştirilemez.

@dataclass(frozen=True)
class KisiSabit:
    name: str
    age: int


print("\n=== frozen=True ile değişmez nesne ===")
c = KisiSabit("Mehmet", 25)
print(f"Yarattık: {c}")

# Şimdi değiştirmeyi DENEYELİM — hata almalıyız.
try:
    c.name = "Ali"  # bu satır patlamalı
except Exception as e:
    print(f"\nHata türü : {type(e).__name__}")
    print(f"Mesaj     : {e}")
    print("→ Yani: bir kez yaratıldı mı, değişmez. Güvende.")


# ─── ÖRNEK 4: frozen olunca BONUS — dict anahtarı yapılabilir ──
# Normal sınıflar dict'in anahtarı olamaz (hashable değiller).
# frozen dataclass HASHABLE — set'e veya dict-key'e koyabilirsin.

print("\n=== Bonus: frozen → hashable ===")
ayarlar = {
    KisiSabit("Ali", 30): "admin",
    KisiSabit("Ayşe", 25): "kullanıcı",
}
print(f"Sözlük anahtarı olarak çalıştı: {ayarlar}")

# Aynısını frozen OLMAYAN ile dene → hata:
try:
    {KisiYeni("Ali", 30): "admin"}
except TypeError as e:
    print(f"\nfrozen OLMAYAN: {e}")
