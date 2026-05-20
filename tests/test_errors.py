"""agentlite.errors — istisna hiyerarşisi için testler.

Hem sınıfların kendisi, hem run/stream'in doğru tipi fırlatması test edilir.
"""

import pytest

from agentlite import (
    Agent,
    AgentError,
    AgentMaxTurnsError,
    PermissionDeniedError,
    ToolExecutionError,
    ToolNotFoundError,
    UnexpectedStopReasonError,
    tool,
)
from agentlite.testing import MockClient, text_response, tool_use_response


# ─── Hiyerarşi doğru kuruldu mu? ──────────────────────────────

def test_tum_istisnalar_agent_error_den_turuyor():
    """except AgentError → hepsini yakalar (kullanıcı dostu)."""
    assert issubclass(AgentMaxTurnsError, AgentError)
    assert issubclass(UnexpectedStopReasonError, AgentError)
    assert issubclass(ToolNotFoundError, AgentError)
    assert issubclass(ToolExecutionError, AgentError)
    assert issubclass(PermissionDeniedError, AgentError)


def test_agent_error_exception_den_turuyor():
    """AgentError standart Exception'dan türemeli."""
    assert issubclass(AgentError, Exception)


# ─── İstisna alanları (.max_turns, .tool_name, .original ...) ──

def test_max_turns_error_max_turns_alanini_tasiyor():
    err = AgentMaxTurnsError(max_turns=5)
    assert err.max_turns == 5
    assert "max_turns" in str(err)


def test_unexpected_stop_error_stop_reason_tasiyor():
    err = UnexpectedStopReasonError(stop_reason="refusal")
    assert err.stop_reason == "refusal"
    assert "refusal" in str(err)


def test_tool_not_found_error_alanlari():
    err = ToolNotFoundError("foo", available=["a", "b"])
    assert err.tool_name == "foo"
    assert err.available == ["a", "b"]


def test_tool_execution_error_original_referansi_tutuyor():
    """Orijinal hatayı .original ile koruyor (debug için kritik)."""
    orig = ValueError("ham hata")
    err = ToolExecutionError("foo", original=orig)
    assert err.tool_name == "foo"
    assert err.original is orig
    assert "ValueError" in str(err)


def test_permission_denied_error_tool_name_tasiyor():
    err = PermissionDeniedError("delete_file")
    assert err.tool_name == "delete_file"


# ─── run() doğru tipi fırlatıyor mu? ──────────────────────────

@tool
def get_weather(city: str) -> str:
    """test."""
    return f"{city}: 22°C"


def test_run_max_turns_asilirsa_AgentMaxTurnsError():
    """Eski 'RuntimeError' yerine AgentMaxTurnsError fırlatılmalı."""
    # Hep tool_use döndüren mock — sonsuza dönmek isteyecek
    client = MockClient(responses=[
        tool_use_response("get_weather", {"city": "X"}) for _ in range(20)
    ])
    agent = Agent(model="x", tools=[get_weather], client=client, max_turns=3)

    with pytest.raises(AgentMaxTurnsError) as excinfo:
        agent.run("dön durma")
    assert excinfo.value.max_turns == 3


def test_run_AgentError_olarak_da_yakalanabilir():
    """except AgentError ile hepsi yakalanır."""
    client = MockClient(responses=[
        tool_use_response("get_weather", {"city": "X"}) for _ in range(20)
    ])
    agent = Agent(model="x", tools=[get_weather], client=client, max_turns=2)

    with pytest.raises(AgentError):  # ← base ile yakala
        agent.run("dön durma")
