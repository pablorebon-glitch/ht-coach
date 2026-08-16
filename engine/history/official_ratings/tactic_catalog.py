from __future__ import annotations

import unicodedata

from models.tactic import Tactic

# The single source of truth for recognized tactic aliases -- the parser,
# any future UI display, and any other service must import this rather than
# keeping their own copy. Includes both this app's own existing translation
# and Hattrick's actual in-game wording where the two differ (confirmed by a
# real Copy Ratings sample: Hattrick says "Atacar por el centro", a verb
# form, while this app's own localization has historically used "Ataque por
# el centro", a noun form).
TACTIC_ALIASES: dict[Tactic, tuple[str, ...]] = {
    Tactic.NORMAL: ("normal",),
    Tactic.ATTACK_IN_MIDDLE: (
        "atacar por el centro",
        "ataque por el centro",
        "attack in the middle",
        "attack through the middle",
    ),
    Tactic.ATTACK_ON_WINGS: (
        "atacar por las bandas",
        "ataque por las bandas",
        "attack on wings",
        "attack on the wings",
    ),
    Tactic.PRESSING: ("presion", "pressing"),
    Tactic.COUNTER_ATTACKS: (
        "contraataques",
        "contraataque",
        "counter-attacks",
        "counter attacks",
    ),
    Tactic.PLAY_CREATIVELY: (
        "jugar creativamente",
        "jugadas creativas",
        "play creatively",
        "creative play",
    ),
    Tactic.LONG_SHOTS: ("tiros lejanos", "long shots"),
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def all_tactic_aliases() -> tuple[str, ...]:
    """Every known alias across every canonical tactic, flattened -- used
    by the parser to find the longest matching tactic-name prefix inside
    a free-text tactic line."""
    return tuple(alias for aliases in TACTIC_ALIASES.values() for alias in aliases)


def resolve_tactic_alias(text: str) -> Tactic | None:
    """Resolves free text (any recognized alias, any supported language)
    to its canonical Tactic, or None if it isn't a recognized alias at
    all. Matching is accent- and case-insensitive and requires an exact
    match against a known alias (not a substring), since tactic names
    are short, fixed phrases with no natural partial-match reading."""
    normalized = _normalize(text)
    for tactic, aliases in TACTIC_ALIASES.items():
        if any(normalized == _normalize(alias) for alias in aliases):
            return tactic
    return None


def find_tactic_alias_prefix(text: str) -> tuple[str, Tactic] | None:
    """Finds the longest known tactic alias that `text` *starts with*
    (used to split a combined "tactic name + quality word" line like
    "Atacar por el centro clase mundial (13)", where there's no
    delimiter between the two free-text phrases). Returns
    (matched_original_text, canonical_tactic) or None."""
    normalized_text = _normalize(text)
    best_match = None
    for alias in sorted(all_tactic_aliases(), key=len, reverse=True):
        normalized_alias = _normalize(alias)
        if normalized_text.startswith(normalized_alias):
            matched_original = text.strip()[: len(alias)].strip()
            tactic = resolve_tactic_alias(alias)
            best_match = (matched_original, tactic)
            break
    return best_match
