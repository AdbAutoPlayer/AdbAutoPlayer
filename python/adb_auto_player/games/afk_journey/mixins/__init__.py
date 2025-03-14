"""AFK Journey Mixins Package."""

from .afk_stages import AFKStagesMixin
from .arcane_labyrinth import ArcaneLabyrinthMixin
from .arena import ArenaMixin
from .assist import AssistMixin
from .dream_realm import DreamRealmMixin
from .duras_trials import DurasTrialsMixin
from .event import EventMixin
from .legend_trial import LegendTrialMixin

__all__: list[str] = [
    "AFKStagesMixin",
    "ArcaneLabyrinthMixin",
    "ArenaMixin",
    "AssistMixin",
    "DreamRealmMixin",
    "DurasTrialsMixin",
    "EventMixin",
    "LegendTrialMixin",
]
