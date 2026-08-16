"""Sector orientation mapping for tactical matchups.

HF-02.2: this used to duplicate its own left/right pairing dicts,
separate from `engine.ratings.sector_rating.MATCHUP_PAIRS` (the
centralized mapping used by the sector-comparison table). Both were
consistent by coincidence, but two independent copies of the same
orientation logic is exactly the duplication the brief calls out --
this module now derives its lookups from that single source of truth.
"""
from engine.ratings.sector_rating import MATCHUP_PAIRS

# Derived once, at import time, from the single centralized mapping --
# never maintained by hand here.
OWN_ATTACK_TO_OPPONENT_DEFENSE = {
    our_sector: opponent_sector
    for matchup_key, our_sector, opponent_sector in MATCHUP_PAIRS
    if matchup_key.startswith("our_")
}

OPPONENT_ATTACK_TO_OWN_DEFENSE = {
    opponent_sector: our_sector
    for matchup_key, our_sector, opponent_sector in MATCHUP_PAIRS
    if matchup_key.startswith("opponent_")
}

ATTACK_SECTORS = tuple(OWN_ATTACK_TO_OPPONENT_DEFENSE.keys())
DEFENSE_SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
)
ALL_SECTORS = DEFENSE_SECTORS + ("midfield",) + ATTACK_SECTORS


def opponent_defense_for_our_attack(attack_sector):
    return OWN_ATTACK_TO_OPPONENT_DEFENSE.get(attack_sector, "")


def own_defense_for_opponent_attack(attack_sector):
    return OPPONENT_ATTACK_TO_OWN_DEFENSE.get(attack_sector, "")
