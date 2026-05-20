"""agentlite — Claude için küçük, odaklı bir agent kütüphanesi.

Kullanıcı `from agentlite import Agent, tool` yapınca buradan alır.

Bu dosya kasten KISA tutulur — paketin "açık API yüzeyi"dir. Kullanıcı
buradaki isimleri görür; geri kalan dahili (alt çizgi ile başlayanlar veya
import edilmeyenler) gizli kalır.
"""

__version__ = "0.2.0"

# Public API — kullanıcının dokunabileceği her şey.
# Dar tut (Modül 7 dersi): yüzey alanı küçük = uyumluluk kolay.
from .agent import Agent
from .subagent import subagent
from .errors import (
    AgentError,
    AgentMaxTurnsError,
    PermissionDeniedError,
    ToolExecutionError,
    ToolNotFoundError,
    UnexpectedStopReasonError,
)
from .events import (
    DoneEvent,
    ErrorEvent,
    StreamEvent,
    TextDeltaEvent,
    ToolResultEvent,
    ToolUseEvent,
)
from .tool import Tool, tool
from .usage import Usage

__all__ = [
    "Agent",
    "Tool",
    "tool",
    "subagent",
    "Usage",
    # Stream events (v0.2)
    "StreamEvent",
    "TextDeltaEvent",
    "ToolUseEvent",
    "ToolResultEvent",
    "DoneEvent",
    "ErrorEvent",
    # Exception hierarchy (v0.2)
    "AgentError",
    "AgentMaxTurnsError",
    "UnexpectedStopReasonError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "PermissionDeniedError",
    "__version__",
]
