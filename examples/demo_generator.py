"""Generator (yield) ile 3 dakikalık tanışma."""

import time


# ─── 1) Normal fonksiyon — tek seferde ─────────────────────────
def normal_sayma(n):
    sonuc = []
    for i in range(n):
        time.sleep(0.3)   # her sayı "yavaş" üretiliyormuş gibi
        sonuc.append(i)
    return sonuc          # ← HEPSİ HAZIR olunca döner


# ─── 2) Generator — parça parça ────────────────────────────────
def yavas_sayma(n):
    for i in range(n):
        time.sleep(0.3)
        yield i           # ← her sayı ÜRETİLİR ÜRETİLMEZ verir


# ─── KARŞILAŞTIRMA ─────────────────────────────────────────────
print("=== NORMAL fonksiyon ===")
print("(beklemen lazım, tüm sonuç bir kerede gelecek)")
baslangic = time.time()
liste = normal_sayma(4)
print(f"Liste: {liste}")
print(f"Süre: {time.time()-baslangic:.1f}s")

print("\n=== GENERATOR (yield) ===")
print("(her sayı ÜRETİLDİĞİNDE ekrana düşecek)")
baslangic = time.time()
for sayi in yavas_sayma(4):
    print(f"  Geldi: {sayi}  (t={time.time()-baslangic:.1f}s)")
print(f"Toplam süre: {time.time()-baslangic:.1f}s")
