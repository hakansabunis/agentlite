"""Sub-agent demo — ana agent + alt-agent + alt-agent'ın kendi araçları.

Senaryo: 'Editor' ana agent, 'researcher' alt-agent'ını çağırıp özet
yazmasını ister. Researcher kendi 'web_search' aracını kullanır.

Mimari:
  USER → Editor (opus) → researcher (haiku) → web_search → researcher → Editor → USER
"""

from agentlite import Agent, subagent, tool
from agentlite.testing import MockClient, text_response, tool_use_response


# ─── Researcher'in kendi araçları ─────────────────────────────
@tool
def web_search(query: str) -> str:
    """Web'de arama yapar (sahte)."""
    return f"Arama sonucu '{query}': AI alanında son ay 3 büyük gelişme var."


# ─── Researcher alt-agenti ────────────────────────────────────
researcher_client = MockClient(responses=[
    # Researcher ilk önce web_search çağırıyor
    tool_use_response("web_search", {"query": "son AI haberleri"}),
    # web_search sonucunu görüp özet veriyor
    text_response("Geçen ay AI'da öne çıkan 3 başlık: çoklu-ajan, ses modelleri, ucuz Opus."),
])

researcher = subagent(
    name="researcher",
    description="Researches a topic by searching the web and summarizing findings.",
    system="You are a research assistant. Be concise.",
    tools=[web_search],
    model="claude-haiku-4-5",
    client=researcher_client,
)

# ─── Editor — ana agent ──────────────────────────────────────
editor_client = MockClient(responses=[
    # Editor önce researcher'a görev veriyor
    tool_use_response("researcher", {"task": "Son ayki AI haberlerini özetle."}),
    # Researcher'in cevabını alıp final yazıyor
    text_response(
        "Aboneler için bu ayın özeti:\n"
        "- Çoklu-ajan mimarileri yaygınlaşıyor\n"
        "- Ses modelleri ucuzladı\n"
        "- Opus modelinin yeni sürümü çıktı"
    ),
])

editor = Agent(
    model="claude-opus-4-7",
    system="You are a newsletter editor. Use the researcher to gather facts.",
    tools=[researcher],
    client=editor_client,
)


# ─── Çalıştır ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("👤 Kullanıcı: Bu hafta için AI haber özeti hazırla")
    print("=" * 60)

    cevap = editor.run("Bu hafta için AI haber özeti hazırla.")
    print(f"\n📰 Editor:\n{cevap}")
    print()
    print(f"--- İstatistikler ---")
    print(f"Editor API çağrısı: {editor_client.create_call_count}")
    print(f"Researcher API çağrısı: {researcher_client.create_call_count}")
    print(f"= toplam {editor_client.create_call_count + researcher_client.create_call_count} çağrı")
