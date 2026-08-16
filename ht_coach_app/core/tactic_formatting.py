"""Alpha 0.6.7 HF-03, Part 7: formats `models.tactic.Tactic` -- the
existing canonical tactic catalog -- into localized display labels. Never
invents unsupported tactics; the enum itself is the single source of truth
for what HT Coach/Hattrick actually implement.
"""
from __future__ import annotations

from models.tactic import Tactic

from ht_coach_app.core.localization import t

_KEY_BY_TACTIC = {
    Tactic.NORMAL: "normal",
    Tactic.ATTACK_IN_MIDDLE: "attack_in_middle",
    Tactic.ATTACK_ON_WINGS: "attack_on_wings",
    Tactic.PRESSING: "pressing",
    Tactic.COUNTER_ATTACKS: "counter_attacks",
    Tactic.PLAY_CREATIVELY: "play_creatively",
    Tactic.LONG_SHOTS: "long_shots",
}


def format_tactic(tactic):
    if isinstance(tactic, str):
        try:
            tactic = Tactic(tactic)
        except ValueError:
            return tactic or ""
    key = _KEY_BY_TACTIC.get(tactic)
    if key is None:
        return getattr(tactic, "value", str(tactic))
    return t(f"match.tactic_option.{key}")


def canonical_tactic_choices():
    return [(tactic, format_tactic(tactic)) for tactic in Tactic]
