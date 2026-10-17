"""Display-only immutable frame; safe to import in the renderer child."""
from dataclasses import dataclass
from .model import View

@dataclass(frozen=True)
class Frame:
    active: bool = False
    view: View = View('', ())
    preview: bool = False
    opponent_switch: bool = False
    offer_layout: bool = False

