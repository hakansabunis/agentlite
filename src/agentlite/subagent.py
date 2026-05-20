"""@subagent — alt-agent fabrika fonksiyonu.

Modül 6 canlı kodu: ana agent'a kendi Agent'lı bir tool ekler.
Tasarım anahtarı: SUB-AGENT BİR TOOL'DUR.

Ana agent için her şey değişmedi — sadece bir tool var, çağırıyor, cevap
alıyor. Arkada o tool'un içinde yeni bir Agent loop'u koşuyor.

Avantajlar:
  - Mevcut Tool sözleşmesi kullanılır (Modül 2)
  - Ana agent'ın tool döngüsü zaten doğru çalışır
  - Context izolasyonu: alt-agent kendi masasında çalışır
"""

from __future__ import annotations

from typing import Any

from .tool import Tool


def subagent(
    *,
    name: str,
    description: str,
    system: str = "",
    tools: list[Tool] | None = None,
    model: str = "claude-haiku-4-5",
    max_turns: int = 10,
    enable_caching: bool = True,
    client: Any = None,
) -> Tool:
    """Alt-agent oluştur, ana agent'a tool olarak verilebilen.

    Args:
        name: ana model'in tool olarak göreceği isim (örn. 'researcher').
        description: ne işe yarar — ana model bunu okuyup ne zaman çağıracağına
            karar verir. ÇOK ÖNEMLİ: model bu metne göre seçim yapar.
        system: alt-agent'ın kendi system promptu (ana ile bağımsız).
        tools: alt-agent'ın kendi araçları (ana ile farklı olabilir).
        model: hangi model — alt-görevler için ucuz/hızlı seçilebilir
            (varsayılan claude-haiku-4-5).
        max_turns: alt-agent için ayrı güvenlik freni.
        enable_caching: alt-agent için prompt caching.
        client: alt-agent'ın Anthropic client'ı (test için).
            None ise her çağrıda yeni bir `anthropic.Anthropic()` kurulur.

    Returns:
        Tool — ana agent'ın araç listesine eklenebilir.

    Örnek:
        researcher = subagent(
            name="researcher",
            description="Searches for facts on a topic.",
            system="You are a research assistant.",
            tools=[web_search],
        )
        parent = Agent(model="...", tools=[researcher, ...])
    """
    # Closure ile sub-agent ayarlarını yakala — her çağrıda
    # taze Agent kuracağız (alt-agent'ın masası izole olsun).
    sub_tools = list(tools or [])
    sub_system = system
    sub_model = model
    sub_max_turns = max_turns
    sub_enable_caching = enable_caching
    sub_client = client

    def _run_sub(task: str) -> str:
        """Alt-agent'ı verilen görevle çalıştır, final metni döndür.

        Bu fonksiyon ana agent'ın tool döngüsünden çağrılır.
        Tool sözleşmesinin call() metoduna uyar.
        """
        # Geç-import (circular import'u kır — agent.py bizi import etmiyor
        # ama biz Agent'ı kullanıyoruz).
        from .agent import Agent

        agent_client = sub_client
        if agent_client is None:
            import anthropic
            agent_client = anthropic.Anthropic()

        sub_agent = Agent(
            model=sub_model,
            system=sub_system,
            tools=sub_tools,
            max_turns=sub_max_turns,
            enable_caching=sub_enable_caching,
            client=agent_client,
        )
        return sub_agent.run(task)

    # Ana agent'ın göreceği Tool — input_schema sade: 'task' alanı.
    # Burada Tool'u DOĞRUDAN inşa ediyoruz (tool() decorator'undan değil)
    # çünkü dahili _run_sub'ı kendimiz tanımlıyoruz; isim ve description
    # parametre olarak geliyor.
    return Tool(
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The task or question to delegate to this subagent. "
                        "Be specific — the subagent has its own context "
                        "and doesn't see this conversation."
                    ),
                },
            },
            "required": ["task"],
        },
        func=_run_sub,
    )


__all__ = ["subagent"]
