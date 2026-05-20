"""Usage dataclass + last_usage entegrasyonu testleri."""

import pytest

from agentlite import Agent, Usage, tool
from agentlite.testing import MockClient, text_response, tool_use_response


# ─── Usage temel davranış ─────────────────────────────────────

def test_usage_default_hepsi_sifir():
    u = Usage()
    assert u.input_tokens == 0
    assert u.output_tokens == 0
    assert u.cache_creation_input_tokens == 0
    assert u.cache_read_input_tokens == 0
    assert u.total() == 0


def test_usage_toplama_birikim_yapar():
    """+ operatörü iki Usage'ı toplar."""
    a = Usage(input_tokens=100, output_tokens=50)
    b = Usage(input_tokens=200, output_tokens=30,
              cache_read_input_tokens=1000)
    c = a + b
    assert c.input_tokens == 300
    assert c.output_tokens == 80
    assert c.cache_read_input_tokens == 1000


def test_usage_total_input_cache_dahil():
    """total_input() = input + cache_creation + cache_read."""
    u = Usage(input_tokens=100, cache_creation_input_tokens=200,
              cache_read_input_tokens=300)
    assert u.total_input() == 600


# ─── Maliyet hesabı ───────────────────────────────────────────

def test_estimate_cost_opus_4_7():
    """Opus 4.7: $5/$25 per 1M tokens."""
    # 1M input + 1M output = $5 + $25 = $30
    u = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    cost = u.estimate_cost_usd("claude-opus-4-7")
    assert cost == pytest.approx(30.0, rel=0.01)


def test_estimate_cost_cache_okuma_ucuz():
    """cache_read 0.1x — net tasarruf."""
    # 1M cache_read on Opus = 1M * $5 * 0.1 = $0.5
    u = Usage(cache_read_input_tokens=1_000_000)
    cost = u.estimate_cost_usd("claude-opus-4-7")
    assert cost == pytest.approx(0.5, rel=0.01)


def test_estimate_cost_bilinmeyen_model_none():
    """Tanınmayan model için None döner (hata değil)."""
    u = Usage(input_tokens=1000)
    assert u.estimate_cost_usd("claude-XYZ-fake") is None


def test_estimate_cost_haiku_opus_ten_5kat_ucuz():
    """Aynı kullanım için haiku opus'tan 5x daha ucuz olmalı."""
    u = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    opus = u.estimate_cost_usd("claude-opus-4-7")
    haiku = u.estimate_cost_usd("claude-haiku-4-5")
    assert opus / haiku == pytest.approx(5.0, rel=0.01)


# ─── Agent.last_usage entegrasyonu ────────────────────────────

@tool
def get_weather(city: str) -> str:
    """test."""
    return f"{city}: 22°C"


def test_last_usage_run_sonrasi_doluyor():
    """Agent.run() bitince agent.last_usage doğru değerleri tutmalı."""
    client = MockClient(responses=[
        text_response("Merhaba",
                      usage={"input_tokens": 100, "output_tokens": 50,
                             "cache_creation_input_tokens": 0,
                             "cache_read_input_tokens": 0}),
    ])
    agent = Agent(model="claude-opus-4-7", client=client)
    agent.run("Selam")

    assert agent.last_usage.input_tokens == 100
    assert agent.last_usage.output_tokens == 50


def test_last_usage_turlar_arasi_birikiyor():
    """İki turlu (tool döngülü) agent için usage toplanmalı."""
    @tool
    def get_data() -> str:
        """."""
        return "data"

    client = MockClient(responses=[
        tool_use_response("get_data", {}, usage={
            "input_tokens": 100, "output_tokens": 20,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
        }),
        text_response("sonuç", usage={
            "input_tokens": 150, "output_tokens": 40,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": 200,
        }),
    ])
    agent = Agent(model="claude-opus-4-7", tools=[get_data], client=client)
    agent.run("test")

    # 100+150 = 250 input, 20+40 = 60 output, 200 cache_read
    assert agent.last_usage.input_tokens == 250
    assert agent.last_usage.output_tokens == 60
    assert agent.last_usage.cache_read_input_tokens == 200


def test_last_usage_her_run_da_sifirlaniyor():
    """Yeni run() önceki usage'ı silmeli (kalıcı birikme olmaz)."""
    client = MockClient(responses=[
        text_response("ilk", usage={"input_tokens": 100, "output_tokens": 50,
                                    "cache_creation_input_tokens": 0,
                                    "cache_read_input_tokens": 0}),
        text_response("ikinci", usage={"input_tokens": 50, "output_tokens": 25,
                                       "cache_creation_input_tokens": 0,
                                       "cache_read_input_tokens": 0}),
    ])
    agent = Agent(model="claude-opus-4-7", client=client)

    agent.run("birinci")
    assert agent.last_usage.input_tokens == 100

    agent.run("ikinci")
    # Yenisi ile değişti, eskiyle TOPLANMADI
    assert agent.last_usage.input_tokens == 50
