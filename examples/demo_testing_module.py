"""Aynı tool döngüsü demosu — bu sefer agentlite.testing public API'sı ile.

KARŞILAŞTIRMA:
    Eski (demo_agent_tool_loop.py): 94 satır, kendi mock'unu kuruyor.
    Yeni (bu dosya):                 ~25 satır kullanıcı kodu.

Mock'un karmaşıklığı KÜTÜPHANE içinde gizli. Kullanıcı sadece
"şu senaryoyu çalıştır" der.
"""

from agentlite import Agent, tool
from agentlite.testing import MockClient, text_response, tool_use_response


# ─── ARAÇ ─────────────────────────────────────────────────────
@tool
def get_weather(city: str) -> str:
    """Bir şehrin hava durumunu döndür."""
    return f"{city}: 22°C, güneşli"


# ─── 2-TURLU SENARYO ──────────────────────────────────────────
# Tek mantıkla: önce model tool ister, sonra final cevap verir.
client = MockClient(responses=[
    tool_use_response("get_weather", {"city": "İstanbul"},
                      text="Hava durumuna bakayım."),
    text_response("İstanbul'da hava 22°C ve güneşli."),
])

agent = Agent(
    model="claude-opus-4-7",
    system="Sen yardımcı bir asistansın.",
    tools=[get_weather],
    client=client,
)

# ─── ÇALIŞTIR ─────────────────────────────────────────────────
sonuc = agent.run("İstanbul'da hava nasıl?")
print(f"Final cevap: {sonuc}")
print(f"API çağrı sayısı: {client.create_call_count}")
assert sonuc == "İstanbul'da hava 22°C ve güneşli."
assert client.create_call_count == 2
print("✅ Tüm assertion'lar geçti")
