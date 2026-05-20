"""@tool decorator — bir Python fonksiyonunu Claude için bir araca dönüştürür.

Bu modül, kütüphanenin KALBİDİR. Kursumuzdaki Modül 2 "Tool sözleşmesi"nin
Python karşılığı: name + description + input_schema + call() bir araya gelir.

Tasarım kararı: kullanıcı SADECE düz bir Python fonksiyonu yazar; gerisini
type hints ve docstring'den biz türetiriz. Hiçbir extra boilerplate yok.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, get_type_hints


# ─── Tool veri sınıfı ──────────────────────────────────────────────
# Bir aracın 4 parçası vardır (Modül 2'deki sözleşmenin tamı):
#   - name:         modelin gördüğü isim
#   - description:  modelin "ne zaman kullanırım?" diye okuduğu metin
#   - input_schema: girdi kuralları (Anthropic API'sine gönderilen JSON Schema)
#   - func:         asıl Python fonksiyonu (call() olarak çalıştırılır)
@dataclass(frozen=True)            # frozen=True → değişmez (immutable); paylaşım güvenli
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., Any]

    # ── Güvenlik bayrakları (Modül 4 dersi) ──
    # read_only=True            : araç hiçbir şeyi değiştirmez → izin sormaya gerek yok
    # requires_confirmation=True: araç çağrılmadan önce kullanıcıya SOR
    # İkisi birden True ise read_only kazanır (sormadan izin ver — Modül 4 mantığı).
    read_only: bool = False
    requires_confirmation: bool = False

    def call(self, **kwargs: Any) -> Any:
        """Aracı verilen argümanlarla çalıştır.

        Modül 2'deki Tool.call() metodunun Python karşılığı.
        Hata yakalamayı agent.py içinde yapacağız — burada saf çalıştırma.
        """
        return self.func(**kwargs)


# ─── Type hint → JSON Schema tipi eşlemesi ──────────────────────────
# JSON Schema tipleri Python tiplerinden farklı isimlerle anılır.
# Bu sözlük "Python tipini → JSON Schema tipini" çevirir.
#
# Modül 2 hatırlat: input_schema'yı modele BURADAKİ tiplerle göndermek
# zorundayız. "str" demek yetmez, "string" demek gerek.
_PYTHON_TO_JSON_TYPES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """Bir Python tipini tek bir JSON Schema parçasına çevirir.

    Örn: str       → {"type": "string"}
         int       → {"type": "integer"}
         list[str] → {"type": "array", "items": {"type": "string"}}  (ileride)
    """
    # Şimdilik sadece basit tipleri destekliyoruz.
    # list[X], Optional[X], Union vs. ileri versiyonlarda eklenecek.
    if py_type in _PYTHON_TO_JSON_TYPES:
        return {"type": _PYTHON_TO_JSON_TYPES[py_type]}
    # Bilinmeyen tip → "string"e düş (sade ve güvenli varsayılan).
    return {"type": "string"}


# ─── ANA DECORATOR (polymorphic — hem @tool hem @tool(...) destekler) ─────
def tool(
    func: Callable[..., Any] | None = None,
    *,
    read_only: bool = False,
    requires_confirmation: bool = False,
) -> Any:
    """Bir fonksiyonu bir Tool'a dönüştürür.

    İki şekilde de çağrılabilir:

        @tool                              # parametresiz — eski usul
        def foo(): ...

        @tool(requires_confirmation=True)  # parametreli — güvenlik bayrağı
        def bar(): ...

        @tool(read_only=True)              # salt-okunur işareti
        def baz(): ...

    Polymorphic decorator pattern: parametresiz çağrıldığında doğrudan
    işler; parametreli çağrıldığında önce ayarları alır, sonra başka bir
    decorator döndürür.
    """
    # ── 1. Çağrı şeklini ayır: @tool mu, @tool(...) mu? ──
    if func is None:
        # @tool(...) ile çağrıldı — bayrakları kapatan başka bir decorator döndür.
        # Bu return edilen lambda, bir sonraki adımda gerçek fonksiyonu alacak.
        def _decorator_with_args(real_func: Callable[..., Any]) -> Tool:
            return _build_tool(real_func, read_only, requires_confirmation)
        return _decorator_with_args

    # @tool (parametresiz) ile çağrıldı — bayraklar False, doğrudan işle.
    return _build_tool(func, read_only=False, requires_confirmation=False)


def _build_tool(
    func: Callable[..., Any],
    read_only: bool,
    requires_confirmation: bool,
) -> Tool:
    """Asıl iş — fonksiyonu inspect ile inceleyip Tool nesnesi üret.

    Bu fonksiyon dahili (alt çizgi ile). Public API 'tool()' bu işi
    her iki çağrı şeklinde de buraya yönlendirir.
    """
    # 1) İsim — basit; fonksiyon adı.
    name = func.__name__

    # 2) Açıklama — docstring.
    description = inspect.getdoc(func)
    if not description:
        raise ValueError(
            f"@tool {name!r}: docstring zorunlu — model bu metni 'ne zaman kullanım?' "
            f"diye okuyacak. Bir cümle yaz."
        )

    # 3) Input schema — type hints'ten üret.
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name not in hints:
            raise ValueError(
                f"@tool {name!r}: '{param_name}' parametresinin tip belirtimi yok. "
                f"Type hint EKLE: '{param_name}: str' gibi."
            )

        properties[param_name] = _python_type_to_json_schema(hints[param_name])

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        input_schema["required"] = required

    # 4) Tool nesnesini üret — güvenlik bayraklarını da içine koy.
    return Tool(
        name=name,
        description=description,
        input_schema=input_schema,
        func=func,
        read_only=read_only,
        requires_confirmation=requires_confirmation,
    )
