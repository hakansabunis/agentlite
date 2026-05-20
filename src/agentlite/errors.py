"""Custom exception hierarchy for agentlite.

Tasarım prensibi:
  AgentError    → tüm agentlite istisnalarının ortak ata sınıfı.
                  Kullanıcı 'except AgentError' yazarak hepsini topluca
                  yakalayabilir. requests / anthropic SDK gibi olgun
                  kütüphanelerin yaptığı yapı.

  Üst 2 (Max/UnexpectedStop) — run()/stream() fırlatır.
  Alt 3 (Tool/Permission)    — fırlatılmaz, sınıf olarak hazır durur.
                               Modül 4 fail-safe: tool hatalarını fırlatmak
                               yerine modele bildirip döngüye devam ederiz.
                               Sınıflar kullanıcının isterse kontrol
                               edebilmesi için public.
"""

from __future__ import annotations


class AgentError(Exception):
    """Tüm agentlite istisnalarının base sınıfı.

    `except AgentError` → kütüphanenin attığı her şeyi yakalar.
    """


# ─── Loop kontrolü istisnaları (fırlatılır) ───────────────────

class AgentMaxTurnsError(AgentError):
    """Agent döngüsü max_turns sınırını aştı.

    Attributes:
        max_turns: izin verilen tur sayısı
        message: hata mesajı
    """

    def __init__(self, max_turns: int) -> None:
        self.max_turns = max_turns
        super().__init__(
            f"Agent loop exceeded max_turns ({max_turns}). "
            f"Increase max_turns or check whether the model is stuck."
        )


class UnexpectedStopReasonError(AgentError):
    """Model beklenmeyen bir stop_reason ile durdu.

    'end_turn' veya 'tool_use' beklenirken model 'refusal',
    'max_tokens' gibi başka bir sebeple durduğunda atılır.

    Attributes:
        stop_reason: API'den gelen orijinal sebep
    """

    def __init__(self, stop_reason: str | None) -> None:
        self.stop_reason = stop_reason
        super().__init__(
            f"Unexpected stop_reason from model: {stop_reason!r}. "
            f"This may be 'refusal', 'max_tokens', or a server-side condition."
        )


# ─── Tool / Permission istisnaları (sınıf olarak hazır) ──────
# Bunlar şu an FIRLATILMIYOR — tool_result'a is_error=True olarak gidiyor.
# Ama kullanıcı modele bildirilen mesajı parse edip bu sınıfları
# instantiate edebilir, ya da gelecekte 'strict=True' modunda fırlatabiliriz.

class ToolNotFoundError(AgentError):
    """Model, agent'a kayıtlı olmayan bir tool çağırdı.

    Pratikte modelin halüsinasyonu işareti.
    """

    def __init__(self, tool_name: str, available: list[str]) -> None:
        self.tool_name = tool_name
        self.available = list(available)
        super().__init__(
            f"Tool {tool_name!r} not registered with agent. "
            f"Available tools: {self.available}"
        )


class ToolExecutionError(AgentError):
    """Kullanıcının tanımladığı tool fonksiyonu çağrılırken hata fırlattı.

    Tool kodunda exception olunca bu sınıfa sarmalanır. Orijinal hataya
    `.original` ile erişilir.
    """

    def __init__(self, tool_name: str, original: BaseException) -> None:
        self.tool_name = tool_name
        self.original = original
        super().__init__(
            f"Tool {tool_name!r} raised "
            f"{type(original).__name__}: {original}"
        )


class PermissionDeniedError(AgentError):
    """Kullanıcı (confirm_fn aracılığıyla) bir tool çağrısını reddetti."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(
            f"User denied permission to call tool {tool_name!r}."
        )


__all__ = [
    "AgentError",
    "AgentMaxTurnsError",
    "UnexpectedStopReasonError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "PermissionDeniedError",
]
