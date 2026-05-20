"""Demo 1: Introspection — bir fonksiyona dışarıdan bakmak."""

import inspect
from typing import get_type_hints


# Sıradan bir fonksiyon — özel hiçbir şey yok.
def greet(name: str, age: int = 25) -> str:
    """Bir kişiyi yaşına göre selamla."""
    return f"Selam {name}, {age} yaşındasın"


print("=== 1. Temel meta bilgiler ===")
print(f"Adı     : {greet.__name__}")           # her fonksiyonun adı vardır
print(f"Doc     : {greet.__doc__}")             # docstring otomatik saklanır

print("\n=== 2. inspect.signature ile parametreler ===")
sig = inspect.signature(greet)
print(f"İmza    : {sig}")                      # (name: str, age: int = 25) -> str

for param_name, param in sig.parameters.items():
    has_default = param.default is not inspect.Parameter.empty
    print(f"  {param_name:6s}  default={'yok' if not has_default else param.default}")

print("\n=== 3. get_type_hints ile tipler ===")
hints = get_type_hints(greet)
print(f"Tipler  : {hints}")                    # {'name': <class 'str'>, ...}

# Bunlardan tek başına HİÇBİRİ özel — Python her fonksiyon hakkında bu bilgiyi
# zaten içinde saklar. inspect/get_type_hints sadece DAHA RAHAT erişim sağlar.
