"""agent.py için birim testleri.

Mock client kullanarak gerçek API'ye gitmeden agent mantığını test ederiz.
Bu sayede testler hızlı (saniyeden az), ücretsiz ve internet gerektirmez.
"""

import pytest

from agentlite import Agent, tool
from agentlite.errors import AgentMaxTurnsError


# ─── Mock yapı taşları (önceki demo'lardan damıtılmış) ────────

class _Block:
    """Anthropic response.content içindeki bir bloğu taklit eder."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Response:
    """Anthropic response objesini taklit eder."""
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


def make_mock_client(responses):
    """Sırayla verilen response listesini döndüren mock client üret.

    responses: her API çağrısında dönülecek _Response listesi.
    """
    class MockClient:
        def __init__(self):
            self.messages = self
            self._iter = iter(responses)
            self.call_count = 0

        def create(self, **kwargs):
            self.call_count += 1
            return next(self._iter)

    return MockClient()


# ─── Temel davranış ───────────────────────────────────────────

def test_agent_basit_metin_cevabi_dondurur():
    """Tool yok, model 'end_turn' diyor → metni döndür."""
    client = make_mock_client([
        _Response(
            content=[_Block(type="text", text="Merhaba!")],
            stop_reason="end_turn",
        )
    ])
    agent = Agent(model="x", client=client)
    assert agent.run("Selam") == "Merhaba!"
    assert client.call_count == 1


def test_agent_tool_dongusunu_dondurur():
    """Model bir tool çağırır, sonra final metin döner."""
    @tool
    def get_weather(city: str) -> str:
        """Hava durumu."""
        return f"{city}: 22°C"

    client = make_mock_client([
        # 1. çağrı: model tool istiyor
        _Response(
            content=[_Block(
                type="tool_use", id="t1",
                name="get_weather", input={"city": "İstanbul"},
            )],
            stop_reason="tool_use",
        ),
        # 2. çağrı: model sonucu işledi, final cevap
        _Response(
            content=[_Block(type="text", text="İstanbul'da 22°C")],
            stop_reason="end_turn",
        ),
    ])
    agent = Agent(model="x", tools=[get_weather], client=client)
    assert agent.run("Hava nasıl?") == "İstanbul'da 22°C"
    assert client.call_count == 2   # tam iki API çağrısı


# ─── Güvenlik freni: max_turns ────────────────────────────────

def test_agent_max_turns_asilirsa_hata_atar():
    """Model sonsuza tool_use diyorsa max_turns'da kesilmeli."""
    @tool
    def noop() -> str:
        """sahte."""
        return ""

    # Hep tool_use döndüren mock — sonsuz döngüye girmeli
    client = make_mock_client([
        _Response(
            content=[_Block(type="tool_use", id=f"t{i}", name="noop", input={})],
            stop_reason="tool_use",
        )
        for i in range(20)
    ])
    agent = Agent(model="x", tools=[noop], client=client, max_turns=3)

    with pytest.raises(AgentMaxTurnsError, match="max_turns"):
        agent.run("dönsene durmadan")


# ─── İzin sistemi testleri (Ders 2E) ──────────────────────────

def test_agent_read_only_tool_icin_izin_sormaz():
    """read_only tool için confirm_fn hiç çağrılmamalı."""
    @tool(read_only=True)
    def safe_read(path: str) -> str:
        """Salt-okunur."""
        return "içerik"

    confirm_calls = []
    def confirm(tool, args):
        confirm_calls.append(tool.name)
        return True

    client = make_mock_client([
        _Response(
            content=[_Block(
                type="tool_use", id="t1",
                name="safe_read", input={"path": "/x"},
            )],
            stop_reason="tool_use",
        ),
        _Response(
            content=[_Block(type="text", text="ok")],
            stop_reason="end_turn",
        ),
    ])
    agent = Agent(
        model="x", tools=[safe_read],
        client=client, confirm_fn=confirm,
    )
    agent.run("oku")

    # read_only olduğu için confirm hiç çağrılmamış olmalı
    assert confirm_calls == []


def test_agent_tehlikeli_tool_icin_izin_sorar():
    """requires_confirmation=True olan tool için confirm_fn çağrılmalı."""
    @tool(requires_confirmation=True)
    def delete_file(path: str) -> str:
        """Sil."""
        return "silindi"

    confirm_calls = []
    def confirm(tool, args):
        confirm_calls.append((tool.name, args))
        return True

    client = make_mock_client([
        _Response(
            content=[_Block(
                type="tool_use", id="t1",
                name="delete_file", input={"path": "/x"},
            )],
            stop_reason="tool_use",
        ),
        _Response(
            content=[_Block(type="text", text="ok")],
            stop_reason="end_turn",
        ),
    ])
    agent = Agent(
        model="x", tools=[delete_file],
        client=client, confirm_fn=confirm,
    )
    agent.run("sil")

    assert confirm_calls == [("delete_file", {"path": "/x"})]


def test_agent_izin_reddedilirse_tool_calismaz():
    """confirm_fn False dönerse tool ASLA çalışmamalı, modele hata bildirilmeli."""
    @tool(requires_confirmation=True)
    def delete_file(path: str) -> str:
        """Sil."""
        raise RuntimeError("BU ÇAĞRILMAMALIYDI!")

    client = make_mock_client([
        _Response(
            content=[_Block(
                type="tool_use", id="t1",
                name="delete_file", input={"path": "/x"},
            )],
            stop_reason="tool_use",
        ),
        _Response(
            content=[_Block(type="text", text="tamam")],
            stop_reason="end_turn",
        ),
    ])
    agent = Agent(
        model="x", tools=[delete_file],
        client=client, confirm_fn=lambda t, a: False,  # her zaman HAYIR
    )

    # Tool gerçekten çalışsaydı RuntimeError fırlardı; fırlamadıysa testimiz geçti
    sonuc = agent.run("sil")
    assert sonuc == "tamam"
