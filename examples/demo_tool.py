"""@tool decorator'unun çalıştığını gözle görelim.

Çalıştırmak için:
    cd C:\\Users\\SABUNIS\\OneDrive\\Desktop\\agentlite
    pip install -e .          # editable install — paketi yerelden yükler
    python examples/demo_tool.py
"""

import json
from agentlite import tool


@tool
def get_weather(city: str, unit: str = "celsius") -> str:
    """Bir şehrin güncel hava durumunu döndürür."""
    return f"{city}: 22°{unit[0].upper()}"


@tool
def calculate(expression: str) -> str:
    """Basit bir matematik ifadesini hesaplar (örn: '2 + 2 * 3')."""
    return str(eval(expression))   # üretimde tehlikeli — sadece demo!


# DEMO: aracın iç yapısını görelim.
for t in [get_weather, calculate]:
    print(f"\n── {t.name} " + "─" * 40)
    print(f"description: {t.description}")
    print(f"input_schema: {json.dumps(t.input_schema, indent=2)}")
    # Aracı doğrudan da çağırabiliriz:
    if t.name == "get_weather":
        print(f"call örneği:  {t.call(city='İstanbul')}")
