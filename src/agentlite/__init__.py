"""agentlite — Claude için küçük, odaklı bir agent kütüphanesi.

Kullanıcı `from agentlite import Agent, tool` yapınca buradan alır.

Bu dosya kasten KISA tutulur — paketin "açık API yüzeyi"dir. Kullanıcı
buradaki isimleri görür; geri kalan dahili (alt çizgi ile başlayanlar veya
import edilmeyenler) gizli kalır.
"""

__version__ = "0.1.0"

# Public API — kullanıcının dokunabileceği her şey.
# Dar tut (Modül 7 dersi): yüzey alanı küçük = uyumluluk kolay.
from .agent import Agent
from .tool import Tool, tool

__all__ = ["Agent", "Tool", "tool", "__version__"]
