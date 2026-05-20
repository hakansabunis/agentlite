"""tool_choice parametresi için testler."""

import pytest

from agentlite import Agent, tool
from agentlite.testing import MockClient, text_response


@tool
def get_weather(city: str) -> str:
    """Hava döndür."""
    return f"{city}: 22°C"


@tool
def search(q: str) -> str:
    """Arama."""
    return f"results for {q}"


# ─── _resolve_tool_choice: string → Anthropic format ──────────

def test_auto_none_donduruyor():
    """'auto' = varsayılan, API'ye gönderilmez."""
    agent = Agent(model="x", tools=[get_weather], client=MockClient())
    assert agent._resolve_tool_choice("auto") is None
    assert agent._resolve_tool_choice(None) is None


def test_any_dict_olarak_doner():
    agent = Agent(model="x", tools=[get_weather], client=MockClient())
    assert agent._resolve_tool_choice("any") == {"type": "any"}


def test_none_dict_olarak_doner():
    agent = Agent(model="x", tools=[get_weather], client=MockClient())
    assert agent._resolve_tool_choice("none") == {"type": "none"}


def test_tool_adi_olarak_string_dict_e_cevrilir():
    """'get_weather' → {'type': 'tool', 'name': 'get_weather'}"""
    agent = Agent(model="x", tools=[get_weather], client=MockClient())
    assert agent._resolve_tool_choice("get_weather") == {
        "type": "tool", "name": "get_weather"
    }


def test_bilinmeyen_tool_adi_hata_atar():
    """Mevcut olmayan tool adı verilirse erken (fail-fast) hata."""
    agent = Agent(model="x", tools=[get_weather], client=MockClient())
    with pytest.raises(ValueError, match="tool yok"):
        agent._resolve_tool_choice("imkansız_tool")


def test_dict_oldugu_gibi_gecer():
    """Geriye dönük: kullanıcı ham Anthropic formatı verebilir."""
    agent = Agent(model="x", tools=[get_weather], client=MockClient())
    raw = {"type": "tool", "name": "get_weather"}
    assert agent._resolve_tool_choice(raw) == raw


# ─── API'ye doğru parametre gidiyor mu? ───────────────────────

def test_default_tool_choice_init_te_belirlenip_api_ye_gider():
    """Agent(tool_choice='any') → API'ye {'type':'any'} gider."""
    client = MockClient(responses=[text_response("ok")])
    agent = Agent(
        model="x", tools=[get_weather], client=client, tool_choice="any",
    )
    agent.run("test")
    assert client.last_create_kwargs.get("tool_choice") == {"type": "any"}


def test_tool_choice_yoksa_api_alanı_yok():
    """tool_choice belirtilmemişse Anthropic'e gönderme — default davranış."""
    client = MockClient(responses=[text_response("ok")])
    agent = Agent(model="x", tools=[get_weather], client=client)
    agent.run("test")
    assert "tool_choice" not in client.last_create_kwargs


def test_tools_yoksa_tool_choice_da_yok():
    """Tool listesi boşsa tool_choice'u API'ye gönderme."""
    client = MockClient(responses=[text_response("ok")])
    agent = Agent(model="x", client=client, tool_choice="any")
    agent.run("test")
    # tools yok → tool_choice da olmamalı (API hata atar)
    assert "tool_choice" not in client.last_create_kwargs
    assert "tools" not in client.last_create_kwargs
