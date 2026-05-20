"""Stream event types — agent.stream()'in yield ettiği tipler.

Modül 8 dersi: kullanıcı tek tip nesne almalı, içinde `type` alanına bakıp
dallanmalı. Bu, "discriminated union" pattern.

Bu modüldeki tüm sınıflar `frozen=True` — Modül 2 dersi: değer-semantiği,
güvenlik, hashable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextDeltaEvent:
    """Model bir metin parçası üretti."""
    text: str
    type: str = "text"


@dataclass(frozen=True)
class ToolUseEvent:
    """Model bir tool çağırmak istiyor (input artık tamam)."""
    name: str
    input: dict[str, Any]
    tool_use_id: str
    type: str = "tool_use"


@dataclass(frozen=True)
class ToolResultEvent:
    """Bir tool çalıştırıldı — sonuç (veya hata) burada."""
    tool_use_id: str
    result: str
    is_error: bool = False
    type: str = "tool_result"


@dataclass(frozen=True)
class DoneEvent:
    """Agent loop bitti — final metin ve toplam usage."""
    final_text: str
    turn_count: int = 0
    # Token usage (ileride agentlite.Usage olacak — şimdilik dict)
    usage: dict[str, int] = field(default_factory=dict)
    type: str = "done"


@dataclass(frozen=True)
class ErrorEvent:
    """Loop bir hatayla durdu."""
    message: str
    type: str = "error"


# Tüm event tiplerinin union'u. Type hint için kullanılır:
#   def stream(...) -> Iterator[StreamEvent]: ...
StreamEvent = (
    TextDeltaEvent
    | ToolUseEvent
    | ToolResultEvent
    | DoneEvent
    | ErrorEvent
)
