from decimal import Decimal

from engine.weekly_training.training_catalog import definition_for
from engine.weekly_training.training_rules import (
    CatalogTrainingRules,
    PlaymakingTrainingRules,
    rule_provider_for,
)
from engine.weekly_training.training_types import TrainingType
from models.position import Position

ALL_POSITIONS = tuple(Position)


# --------------------------------------------------------------------------
# Playmaking backward compatibility — the single most important test in
# this file: proves the new catalog-driven system computes byte-identical
# factors to the untouched, original PlaymakingTrainingRules class that
# every existing Copa/coverage test (and Pablo's real saved data) already
# depends on.
# --------------------------------------------------------------------------

def test_playmaking_full_and_reduced_tiers_match_between_original_and_catalog():
    """The two tiers that actually drive existing behavior — IM full,
    winger reduced — are identical between the untouched original class
    and the new catalog definition."""
    original = PlaymakingTrainingRules()
    catalog_equivalent = CatalogTrainingRules(definition_for(TrainingType.PLAYMAKING))

    assert original.factor_for_position(Position.INNER_MIDFIELDER) == (
        catalog_equivalent.factor_for_position(Position.INNER_MIDFIELDER)
    ) == Decimal("1")
    assert original.factor_for_position(Position.WINGER) == (
        catalog_equivalent.factor_for_position(Position.WINGER)
    ) == Decimal("0.5")


def test_playmaking_very_small_tier_is_a_documented_new_behavior_not_yet_active():
    """Real, deliberate finding from building the catalog against the
    Alpha 0.5.8.5 training matrix: the *original* PlaymakingTrainingRules
    (still the one `rule_provider_for("PLAYMAKING")` returns) treats every
    position other than IM/Winger as exactly 0 — there was never a
    "very small" tier for Playmaking. The new canonical matrix in this
    sprint's brief explicitly adds "very-small effect: every other
    player who participated" for Playmaking, which is a *behavior
    change*, not a restatement of the existing rule.

    Per this sprint's own instruction ("preserve existing behavior
    unless it contradicts the canonical model") this is a genuine
    contradiction, so it's surfaced here rather than silently applied:
    `rule_provider_for("PLAYMAKING")` intentionally keeps returning the
    original, unchanged class, so existing coverage numbers for
    already-tracked players don't shift. The catalog's Playmaking
    definition exists for consistency with the other 11 types and is
    available via `CatalogTrainingRules(definition_for(TrainingType.PLAYMAKING))`
    if a future sprint decides to adopt the very-small tier."""
    original = PlaymakingTrainingRules()
    catalog_equivalent = CatalogTrainingRules(definition_for(TrainingType.PLAYMAKING))

    for position in (
        Position.GOALKEEPER,
        Position.CENTRAL_DEFENDER,
        Position.WING_BACK,
        Position.FORWARD,
    ):
        assert original.factor_for_position(position) == Decimal("0")
        assert catalog_equivalent.factor_for_position(position) == Decimal("0.1")


def test_rule_provider_for_playmaking_returns_the_original_untouched_class():
    provider = rule_provider_for("PLAYMAKING")
    assert isinstance(provider, PlaymakingTrainingRules)


def test_rule_provider_for_is_case_insensitive_and_tolerant():
    assert rule_provider_for("playmaking") is not None
    assert isinstance(rule_provider_for("playmaking"), PlaymakingTrainingRules)
    assert rule_provider_for("not_a_real_type") is None
    assert rule_provider_for(None) is None


def test_rule_provider_for_every_official_type_returns_a_provider():
    for training_type in TrainingType:
        provider = rule_provider_for(training_type.value)
        assert provider is not None
        assert provider.training_type == training_type.value


# --------------------------------------------------------------------------
# CatalogTrainingRules: single-skill types
# --------------------------------------------------------------------------

def test_catalog_rules_defending():
    rules = rule_provider_for(TrainingType.DEFENDING.value)
    assert rules.factor_for_position(Position.CENTRAL_DEFENDER) == Decimal("1")
    assert rules.factor_for_position(Position.WING_BACK) == Decimal("1")
    assert rules.factor_for_position(Position.FORWARD) == Decimal("0.1")


def test_catalog_rules_goalkeeping_has_zero_for_outfield_players():
    rules = rule_provider_for(TrainingType.GOALKEEPING.value)
    assert rules.factor_for_position(Position.GOALKEEPER) == Decimal("1")
    assert rules.factor_for_position(Position.FORWARD) == Decimal("0")


def test_catalog_rules_accepts_string_position_like_lineup_entries_do():
    rules = rule_provider_for(TrainingType.SCORING.value)
    assert rules.factor_for_position("FORWARD") == Decimal("1")
    assert rules.factor_for_position("GOALKEEPER") == Decimal("0.1")


def test_catalog_rules_unknown_legacy_position_is_safe_zero():
    rules = rule_provider_for(TrainingType.PLAYMAKING.value)
    assert rules.factor_for_position("SOME_LEGACY_POSITION") == Decimal("0")


# --------------------------------------------------------------------------
# CatalogTrainingRules: multi-skill (Shooting)
# --------------------------------------------------------------------------

def test_catalog_rules_shooting_reports_both_skills():
    rules = rule_provider_for(TrainingType.SHOOTING.value)
    assert set(rules.trained_skills) == {"scoring", "set_pieces"}
    factors = rules.factors_for_position(Position.FORWARD)
    assert factors["scoring"] == Decimal("0.5")
    assert factors["set_pieces"] == Decimal("0.1")


def test_catalog_rules_shooting_primary_skill_is_scoring():
    rules = rule_provider_for(TrainingType.SHOOTING.value)
    assert rules.primary_skill == "scoring"
    # factor_for_position reports the *strongest* effect across skills,
    # which for Shooting is scoring's REDUCED (0.5) everywhere.
    assert rules.factor_for_position(Position.GOALKEEPER) == Decimal("0.5")


# --------------------------------------------------------------------------
# capacity_for_formation / exposure_for_entry still work via the base class
# --------------------------------------------------------------------------

def test_capacity_for_formation_works_for_a_generalized_type():
    from models.formations import FORMATION_352

    rules = rule_provider_for(TrainingType.DEFENDING.value)
    capacity = rules.capacity_for_formation(FORMATION_352)
    # 3-5-2: 3 central defenders train full under Defending.
    assert capacity.full_slots == 3


def test_exposure_for_entry_uses_primary_skill_factor():
    from engine.weekly_training.models import ExposureConfidence, WeeklyMatchLineupEntry

    rules = rule_provider_for(TrainingType.DEFENDING.value)
    entry = WeeklyMatchLineupEntry(
        player_id="p1",
        player_name="Test Player",
        slot_id="CENTRAL_DEFENDER:1",
        position="CENTRAL_DEFENDER",
        side="CENTER",
    )
    exposure = rules.exposure_for_entry("match1", entry, "test", ExposureConfidence.ASSUMED)
    assert exposure.training_factor == Decimal("1")
    assert exposure.effective_training_minutes == Decimal("90")


# --------------------------------------------------------------------------
# effect_for_position / trainable_positions convenience helpers
# --------------------------------------------------------------------------

def test_effect_for_position_returns_typed_effect_not_raw_weight():
    from engine.weekly_training.training_effects import TrainingEffect

    rules = rule_provider_for(TrainingType.DEFENSIVE_POSITIONS.value)
    assert rules.effect_for_position(Position.CENTRAL_DEFENDER) == TrainingEffect.REDUCED
    assert rules.effect_for_position(Position.FORWARD) == TrainingEffect.VERY_SMALL


def test_catalog_rules_definition_property_and_unknown_position_handling():
    from engine.weekly_training.training_effects import TrainingEffect

    rules = rule_provider_for(TrainingType.DEFENDING.value)
    assert rules.definition.training_type == TrainingType.DEFENDING
    assert rules.factor_for_position("NOT_A_REAL_POSITION") == Decimal("0")
    assert rules.effect_for_position("NOT_A_REAL_POSITION") == TrainingEffect.NONE
    assert rules.factors_for_position("NOT_A_REAL_POSITION") == {"defending": Decimal("0")}


def test_catalog_rules_effect_for_position_defaults_to_primary_skill():
    from engine.weekly_training.training_effects import TrainingEffect

    rules = rule_provider_for(TrainingType.SHOOTING.value)
    assert rules.effect_for_position(Position.FORWARD) == TrainingEffect.REDUCED
    assert rules.effect_for_position(Position.FORWARD, "set_pieces") == (
        TrainingEffect.VERY_SMALL
    )


def test_trainable_positions_delegates_to_definition():
    rules = rule_provider_for(TrainingType.GOALKEEPING.value)
    assert rules.trainable_positions() == (Position.GOALKEEPER,)
