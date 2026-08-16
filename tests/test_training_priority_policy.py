import pytest

from engine.weekly_training.training_priority_policy import (
    TrainingPolicyType,
    build_policy,
)
from engine.weekly_training.training_types import TrainingType

EXPECTED_POLICY_TYPES = {
    TrainingType.GENERAL: TrainingPolicyType.TEAM_WIDE,
    TrainingType.SET_PIECES: TrainingPolicyType.TEAM_WIDE,
    TrainingType.DEFENDING: TrainingPolicyType.FIXED_POSITIONAL_CAPACITY,
    TrainingType.SCORING: TrainingPolicyType.SINGLE_POSITION,
    TrainingType.WINGER: TrainingPolicyType.MULTI_EFFECT_POSITIONAL_CAPACITY,
    TrainingType.SHOOTING: TrainingPolicyType.BROAD_PARTICIPATION,
    TrainingType.SHORT_PASSES: TrainingPolicyType.FIXED_POSITIONAL_CAPACITY,
    TrainingType.PLAYMAKING: TrainingPolicyType.MULTI_EFFECT_POSITIONAL_CAPACITY,
    TrainingType.GOALKEEPING: TrainingPolicyType.SINGLE_POSITION,
    TrainingType.THROUGH_PASSES: TrainingPolicyType.FIXED_POSITIONAL_CAPACITY,
    TrainingType.DEFENSIVE_POSITIONS: TrainingPolicyType.FIXED_POSITIONAL_CAPACITY,
    TrainingType.WING_ATTACKS: TrainingPolicyType.FIXED_POSITIONAL_CAPACITY,
}

# (training_type, expected_effect, expected_positions, expected_per_match, expected_weekly)
EXPECTED_CAPACITY_GROUPS = [
    ("DEFENDING", "FULL", {"CENTRAL_DEFENDER", "WING_BACK"}, 5, 10),
    ("SCORING", "FULL", {"FORWARD"}, 3, 6),
    ("WINGER", "FULL", {"WINGER"}, 2, 4),
    ("WINGER", "REDUCED", {"WING_BACK"}, 2, 4),
    ("PLAYMAKING", "FULL", {"INNER_MIDFIELDER"}, 3, 6),
    ("PLAYMAKING", "REDUCED", {"WINGER"}, 2, 4),
    ("GOALKEEPING", "FULL", {"GOALKEEPER"}, 1, 2),
    ("WING_ATTACKS", "FULL", {"FORWARD", "WINGER"}, 5, 10),
]


@pytest.mark.parametrize("training_type", list(TrainingType))
def test_every_training_type_produces_a_policy(training_type):
    policy = build_policy(training_type)
    assert policy is not None
    assert policy.training_type == training_type


@pytest.mark.parametrize("training_type,expected", list(EXPECTED_POLICY_TYPES.items()))
def test_policy_type_matches_catalog_derived_classification(training_type, expected):
    policy = build_policy(training_type)
    assert policy.policy_type == expected


@pytest.mark.parametrize(
    "training_type,effect,positions,per_match,weekly", EXPECTED_CAPACITY_GROUPS
)
def test_capacity_groups_match_brief_examples(training_type, effect, positions, per_match, weekly):
    policy = build_policy(training_type)
    group = next(g for g in policy.capacity_groups if g.effect.value == effect)
    assert {p.value for p in group.positions} == positions
    assert group.per_match_capacity == per_match
    assert group.weekly_capacity == weekly


def test_team_wide_types_have_no_capacity_groups():
    for training_type in (TrainingType.GENERAL, TrainingType.SET_PIECES):
        policy = build_policy(training_type)
        assert policy.capacity_groups == ()
        assert policy.has_fixed_quota is False


def test_broad_participation_has_no_capacity_groups():
    policy = build_policy(TrainingType.SHOOTING)
    assert policy.capacity_groups == ()
    assert policy.has_fixed_quota is False


def test_positional_policies_have_fixed_quota():
    for training_type in (
        TrainingType.DEFENDING,
        TrainingType.SCORING,
        TrainingType.WINGER,
        TrainingType.GOALKEEPING,
        TrainingType.SHORT_PASSES,
        TrainingType.PLAYMAKING,
        TrainingType.THROUGH_PASSES,
        TrainingType.DEFENSIVE_POSITIONS,
        TrainingType.WING_ATTACKS,
    ):
        policy = build_policy(training_type)
        assert policy.has_fixed_quota is True
        assert len(policy.capacity_groups) >= 1


def test_multi_effect_groups_are_ordered_strongest_first():
    policy = build_policy(TrainingType.PLAYMAKING)
    effects = [g.effect.value for g in policy.capacity_groups]
    assert effects == ["FULL", "REDUCED"]


def test_matches_per_week_is_configurable_not_hardcoded():
    policy = build_policy(TrainingType.DEFENDING, matches_per_week=3)
    group = policy.capacity_groups[0]
    assert group.weekly_capacity == group.per_match_capacity * 3


def test_unknown_training_type_returns_none():
    assert build_policy("SOME_FUTURE_TYPE_NOBODY_KNOWS") is None


def test_defensive_positions_has_no_full_tier_only_reduced():
    """A training type where no position reaches FULL at all is still
    a valid FIXED_POSITIONAL_CAPACITY policy at REDUCED tier -- the
    wizard must not assume a FULL group always exists."""
    policy = build_policy(TrainingType.DEFENSIVE_POSITIONS)
    assert len(policy.capacity_groups) == 1
    assert policy.capacity_groups[0].effect.value == "REDUCED"


def test_capacity_groups_cover_every_position_at_most_once():
    """No position should appear in more than one capacity group for
    the same training type."""
    for training_type in TrainingType:
        policy = build_policy(training_type)
        seen = []
        for group in policy.capacity_groups:
            seen.extend(group.positions)
        assert len(seen) == len(set(seen))


def test_policy_derivation_never_hardcodes_playmaking_or_defending_examples():
    """Structural guarantee: the module never special-cases a specific
    TrainingType by name -- verified by scanning for the literal
    catalog enum member names inside the derivation function's own
    source (aside from the module-level import lines)."""
    import inspect

    from engine.weekly_training import training_priority_policy

    source = inspect.getsource(training_priority_policy.build_policy)
    for forbidden in ("TrainingType.PLAYMAKING", "TrainingType.DEFENDING"):
        assert forbidden not in source
