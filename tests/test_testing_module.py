"""agentlite.testing modülünün KENDİSİ için testler.

Kütüphanenin sunduğu test araçları çalışıyor mu? — bunu test ediyoruz.
"""

import pytest

from agentlite import Agent, tool
from agentlite.testing import (
    MockClient,
    text_response,
    text_stream,
    tool_use_response,
    tool_use_stream,
)


# ─── MockClient temel davranış ────────────────────────────────

def test_mock_client_create_response_sirasinda_donduruyor():
    """create() çağrıları responses listesindeki sırayla döner."""
    client = MockClient(responses=[
        text_response("ilk"),
        text_response("ikinci"),
    ])
    r1 = client.create(model="x", messages=[])
    r2 = client.create(model="x", messages=[])
    assert r1.content[0].text == "ilk"
    assert r2.content[0].text == "ikinci"
    assert client.create_call_count == 2


def test_mock_client_response_kuyrugu_tukenirse_hata():
    """Response kalmayınca anlamlı bir hata atmalı."""
    client = MockClient(responses=[text_response("tek")])
    client.create(model="x", messages=[])
    with pytest.raises(RuntimeError, match="response kuyruğu boş"):
        client.create(model="x", messages=[])


def test_mock_client_last_create_kwargs_tutuyor():
    """Test assertion'ları için son çağrı argümanlarını saklamalı."""
    client = MockClient(responses=[text_response("ok")])
    client.create(model="claude-opus-4-7", messages=[{"role": "user", "content": "hi"}])
    assert client.last_create_kwargs["model"] == "claude-opus-4-7"
    assert client.last_create_kwargs["messages"][0]["content"] == "hi"


# ─── Factory'ler doğru şekil üretiyor mu? ─────────────────────

def test_text_response_dogru_yapida():
    r = text_response("merhaba")
    assert r.stop_reason == "end_turn"
    assert r.content[0].type == "text"
    assert r.content[0].text == "merhaba"


def test_tool_use_response_dogru_yapida():
    r = tool_use_response("foo", {"x": 1}, text="düşünüyorum")
    assert r.stop_reason == "tool_use"
    # 2 blok olmalı: text + tool_use
    assert len(r.content) == 2
    assert r.content[0].type == "text"
    assert r.content[1].type == "tool_use"
    assert r.content[1].name == "foo"
    assert r.content[1].input == {"x": 1}


# ─── Entegrasyon: agent + MockClient ──────────────────────────

def test_agent_mock_client_ile_tool_loop():
    """Tüm v0.1 entegrasyon testimiz ama yeni testing API'siyle."""
    @tool
    def get_weather(city: str) -> str:
        """test."""
        return f"{city}: sunny"

    client = MockClient(responses=[
        tool_use_response("get_weather", {"city": "Istanbul"}),
        text_response("Istanbul'da güneşli."),
    ])
    agent = Agent(model="x", tools=[get_weather], client=client)

    assert agent.run("hava?") == "Istanbul'da güneşli."
    assert client.create_call_count == 2


# ─── Streaming factory'leri ───────────────────────────────────

def test_text_stream_event_uretiyor():
    """text_stream() doğru event akışı üretir."""
    events = text_stream("merhaba dünya")
    types = [e.type for e in events]
    # Sırayla: block_start → 2 delta → block_stop → message_delta
    assert types[0] == "content_block_start"
    assert types[-1] == "message_delta"
    # En az 2 delta var (2 kelime)
    delta_count = sum(1 for t in types if t == "content_block_delta")
    assert delta_count >= 2


def test_tool_use_stream_input_json_olarak_parça_uretiyor():
    """tool_use_stream input'u JSON parça parça yayınlar (Anthropic davranışı)."""
    events = tool_use_stream("foo", {"x": 1, "y": 2})
    # input_json_delta event'lerini topla
    deltas = [e for e in events if e.type == "content_block_delta"
              and e.delta.type == "input_json_delta"]
    assert len(deltas) >= 1
    # Hepsini birleştirince doğru JSON çıkmalı
    full = "".join(d.delta.partial_json for d in deltas)
    import json
    assert json.loads(full) == {"x": 1, "y": 2}


def test_agent_stream_mock_streams_ile():
    """Agent.stream() yeni testing stream factory'leriyle çalışır mı?"""
    from agentlite import DoneEvent, TextDeltaEvent, ToolUseEvent

    @tool
    def get_weather(city: str) -> str:
        """test."""
        return f"{city}: 22°C"

    client = MockClient(streams=[
        tool_use_stream("get_weather", {"city": "Istanbul"},
                        text="Bakayım."),
        text_stream("İstanbul'da 22°C."),
    ])
    agent = Agent(model="x", tools=[get_weather], client=client)

    events = list(agent.stream("hava?"))
    event_types = [e.type for e in events]
    # En az şu olmalı: text → tool_use → tool_result → text → done
    assert "tool_use" in event_types
    assert "tool_result" in event_types
    assert "done" in event_types
    assert client.stream_call_count == 2
