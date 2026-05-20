"""@subagent factory için testler."""

import pytest

from agentlite import Agent, Tool, subagent, tool
from agentlite.testing import MockClient, text_response, tool_use_response


# ─── Temel davranış ───────────────────────────────────────────

def test_subagent_tool_donduruyor():
    """subagent(...) çağrısı bir Tool nesnesi vermeli."""
    sub = subagent(
        name="helper",
        description="A helper agent.",
        system="You help.",
    )
    assert isinstance(sub, Tool)
    assert sub.name == "helper"
    assert sub.description == "A helper agent."


def test_subagent_input_schema_task_alani_iceriyor():
    """Tool olarak görünen alt-agent'ın input schema'sı 'task' parametresi olmalı."""
    sub = subagent(name="x", description="d", system="s")
    assert "task" in sub.input_schema["properties"]
    assert sub.input_schema["required"] == ["task"]


def test_subagent_call_metni_dondurur():
    """Sub-agent çağrıldığında kendi loop'unu koşup metni döndürmeli."""
    sub_client = MockClient(responses=[text_response("subagent cevabı")])
    sub = subagent(
        name="helper",
        description="d",
        system="You are a helper.",
        client=sub_client,
    )
    # Doğrudan call et (parent simülasyonu)
    result = sub.call(task="bir iş yap")
    assert result == "subagent cevabı"
    assert sub_client.create_call_count == 1


# ─── Parent + subagent entegrasyonu ───────────────────────────

def test_parent_subagent_i_tool_gibi_cagiriyor():
    """Ana agent'ın tool döngüsü subagent'ı normal tool gibi tetiklemeli."""
    # Sub-agent: bir görev alıp 'analiz tamam' der
    sub_client = MockClient(responses=[text_response("analiz tamam")])
    researcher = subagent(
        name="researcher",
        description="Researches things.",
        system="You research.",
        client=sub_client,
    )

    # Ana agent: önce researcher'ı çağırır, sonra final cevap üretir
    parent_client = MockClient(responses=[
        tool_use_response("researcher", {"task": "konuyu araştır"}),
        text_response("Araştırmaya göre: analiz tamam"),
    ])
    parent = Agent(model="x", tools=[researcher], client=parent_client)

    sonuc = parent.run("konuyu araştır ve özetle")
    assert sonuc == "Araştırmaya göre: analiz tamam"
    # Hem ana hem alt agent kendi API çağrılarını yapmış olmalı
    assert parent_client.create_call_count == 2  # tool_use + final
    assert sub_client.create_call_count == 1     # subagent kendi loop'u


def test_subagent_in_kendi_tool_lari_var():
    """Sub-agent'a kendi tool'larını verebilirsin (ana agent görmez)."""
    @tool
    def secret_calc(x: int) -> int:
        """secret."""
        return x * 100

    sub_client = MockClient(responses=[
        tool_use_response("secret_calc", {"x": 5}),
        text_response("500 hesaplandı."),
    ])
    sub = subagent(
        name="calculator",
        description="Does math.",
        system="You calc.",
        tools=[secret_calc],
        client=sub_client,
    )
    result = sub.call(task="5'i hesapla")
    assert result == "500 hesaplandı."


def test_subagent_kendi_max_turns_unu_kullanir():
    """Sub-agent'ın max_turns'ü ana agent'tan ayrı."""
    from agentlite.errors import AgentMaxTurnsError

    @tool
    def loopy() -> str:
        """loop."""
        return ""

    # Sub-agent sonsuza dönmek istesin
    sub_client = MockClient(responses=[
        tool_use_response("loopy", {}) for _ in range(10)
    ])
    sub = subagent(
        name="bad",
        description="d",
        system="s",
        tools=[loopy],
        max_turns=2,           # alt-agent'a özel limit
        client=sub_client,
    )

    # Doğrudan çağırırsak alt-agent'ın limiti devreye girer
    with pytest.raises(AgentMaxTurnsError) as excinfo:
        sub.call(task="dön durma")
    assert excinfo.value.max_turns == 2
