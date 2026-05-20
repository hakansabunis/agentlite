"""tool.py için birim testleri.

Her test TEK bir davranışı doğrular. Bir test fail olursa, hangi özellikte
bug olduğunu adından anlamalıyız.
"""

import pytest

from agentlite import Tool, tool


# ─── @tool decorator'ünün temel davranışı ─────────────────────

def test_tool_bir_tool_nesnesi_uretir():
    """@tool sıradan bir fonksiyonu Tool nesnesine çevirmeli."""
    @tool
    def hello(name: str) -> str:
        """Birini selamla."""
        return f"Hi {name}"

    assert isinstance(hello, Tool)


def test_tool_fonksiyon_adini_alir():
    """Tool.name fonksiyonun adından gelir."""
    @tool
    def get_weather(city: str) -> str:
        """Hava durumu."""
        return ""

    assert get_weather.name == "get_weather"


def test_tool_docstringi_description_yapar():
    """Tool.description docstring'den gelir."""
    @tool
    def my_func(x: str) -> str:
        """Bu açıklama olmalı."""
        return ""

    assert my_func.description == "Bu açıklama olmalı."


# ─── JSON schema üretimi ──────────────────────────────────────

def test_tool_schemada_zorunlu_parametre_isaretlenir():
    """Varsayılanı olmayan parametre 'required' listesine girer."""
    @tool
    def f(zorunlu: str, opsiyonel: int = 5) -> str:
        """test."""
        return ""

    assert "zorunlu" in f.input_schema["required"]
    assert "opsiyonel" not in f.input_schema.get("required", [])


def test_tool_python_tipini_json_tipine_cevirir():
    """str → 'string', int → 'integer', bool → 'boolean'."""
    @tool
    def f(s: str, i: int, b: bool) -> str:
        """test."""
        return ""

    props = f.input_schema["properties"]
    assert props["s"]["type"] == "string"
    assert props["i"]["type"] == "integer"
    assert props["b"]["type"] == "boolean"


# ─── Güvenlik bayrakları (Ders 2E) ────────────────────────────

def test_tool_read_only_bayragi_varsayilan_false():
    """Bayrak belirtilmezse read_only=False olmalı."""
    @tool
    def f(x: str) -> str:
        """test."""
        return ""

    assert f.read_only is False
    assert f.requires_confirmation is False


def test_tool_read_only_true_yapilabilir():
    """@tool(read_only=True) → Tool.read_only=True."""
    @tool(read_only=True)
    def safe_read(path: str) -> str:
        """Salt-okunur."""
        return ""

    assert safe_read.read_only is True


def test_tool_requires_confirmation_true_yapilabilir():
    """@tool(requires_confirmation=True) → bayrak set olmalı."""
    @tool(requires_confirmation=True)
    def danger(path: str) -> str:
        """Tehlikeli."""
        return ""

    assert danger.requires_confirmation is True


# ─── Hata durumları (kullanıcıyı yanlış kullanımdan koru) ─────

def test_tool_docstring_yoksa_hata_atar():
    """Docstring olmayan fonksiyona @tool fırlamalı."""
    with pytest.raises(ValueError, match="docstring zorunlu"):
        @tool
        def no_doc(x: str) -> str:
            return ""


def test_tool_type_hint_yoksa_hata_atar():
    """Type hint olmayan parametreye @tool fırlamalı."""
    with pytest.raises(ValueError, match="tip belirtimi yok"):
        @tool
        def no_type(x) -> str:
            """eksik tip."""
            return ""


# ─── Tool.call gerçekten fonksiyonu çağırır ───────────────────

def test_tool_call_fonksiyonu_calistirir():
    """Tool.call kullanıcının orijinal fonksiyonunu çağırmalı."""
    @tool
    def topla(a: int, b: int) -> int:
        """topla."""
        return a + b

    assert topla.call(a=2, b=3) == 5
