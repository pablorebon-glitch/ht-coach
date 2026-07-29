from engine.history.official_ratings.tactic_catalog import (
    TACTIC_ALIASES,
    all_tactic_aliases,
    find_tactic_alias_prefix,
    resolve_tactic_alias,
)
from models.tactic import Tactic


def test_all_seven_tactics_have_aliases():
    assert set(TACTIC_ALIASES.keys()) == set(Tactic)
    for tactic, aliases in TACTIC_ALIASES.items():
        assert len(aliases) >= 1


def test_resolve_tactic_alias_exact_match():
    assert resolve_tactic_alias("Normal") == Tactic.NORMAL
    assert resolve_tactic_alias("pressing") == Tactic.PRESSING
    assert resolve_tactic_alias("Presión") == Tactic.PRESSING


def test_resolve_tactic_alias_unknown_returns_none():
    assert resolve_tactic_alias("Some Unknown Tactic") is None


def test_resolve_tactic_alias_both_wordings_of_attack_in_middle():
    assert resolve_tactic_alias("Atacar por el centro") == Tactic.ATTACK_IN_MIDDLE
    assert resolve_tactic_alias("Ataque por el centro") == Tactic.ATTACK_IN_MIDDLE
    assert resolve_tactic_alias("Attack in the Middle") == Tactic.ATTACK_IN_MIDDLE


def test_find_tactic_alias_prefix_splits_name_from_trailing_text():
    match = find_tactic_alias_prefix("Atacar por el centro clase mundial (13)")
    assert match is not None
    matched_text, tactic = match
    assert matched_text == "Atacar por el centro"
    assert tactic == Tactic.ATTACK_IN_MIDDLE


def test_find_tactic_alias_prefix_no_match_for_unknown_text():
    assert find_tactic_alias_prefix("Something completely unrelated") is None


def test_find_tactic_alias_prefix_prefers_longest_alias():
    """"Atacar por las bandas" must not be mistaken for a shorter
    unrelated alias that happens to share a prefix."""
    match = find_tactic_alias_prefix("Atacar por las bandas excelente (7)")
    assert match is not None
    assert match[1] == Tactic.ATTACK_ON_WINGS


def test_all_tactic_aliases_are_flattened_and_non_empty():
    aliases = all_tactic_aliases()
    assert len(aliases) >= len(Tactic)
    assert "normal" in aliases
