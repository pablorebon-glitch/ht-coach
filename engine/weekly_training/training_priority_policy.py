from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.weekly_training.training_catalog import definition_for
from engine.weekly_training.training_effects import TrainingEffect, best_effect
from models.formations import FORMATIONS
from models.position import Position

DEFAULT_MATCHES_PER_WEEK = 2


class TrainingPolicyType(str, Enum):
    """How a training type's wizard should behave. Derived entirely
    from the shape of its TrainingDefinition -- never assigned by
    hand per training type."""

    FIXED_POSITIONAL_CAPACITY = "FIXED_POSITIONAL_CAPACITY"
    MULTI_EFFECT_POSITIONAL_CAPACITY = "MULTI_EFFECT_POSITIONAL_CAPACITY"
    BROAD_PARTICIPATION = "BROAD_PARTICIPATION"
    TEAM_WIDE = "TEAM_WIDE"
    SINGLE_POSITION = "SINGLE_POSITION"


@dataclass(frozen=True)
class CapacityGroup:
    """One wizard step's worth of capacity: every position sharing the
    same best-achievable effect tier, and how many players can occupy
    that tier per match and across the two recorded weekly matches."""

    effect: TrainingEffect
    positions: tuple[Position, ...]
    per_match_capacity: int
    weekly_capacity: int


@dataclass(frozen=True)
class TrainingPriorityPolicy:
    """Everything the Training Priority Wizard needs to build its steps
    for one training type -- fully derived from the canonical catalog.
    `capacity_groups` is empty for TEAM_WIDE/BROAD_PARTICIPATION types,
    which have no fixed positional quota to select against."""

    training_type: object
    policy_type: TrainingPolicyType
    capacity_groups: tuple[CapacityGroup, ...] = ()
    matches_per_week: int = DEFAULT_MATCHES_PER_WEEK

    @property
    def has_fixed_quota(self) -> bool:
        return self.policy_type not in (
            TrainingPolicyType.TEAM_WIDE,
            TrainingPolicyType.BROAD_PARTICIPATION,
        )


def formation_position_maximums() -> dict:
    """{Position: max legal count of that position across every
    canonical Hattrick formation HT Coach knows about} -- e.g.
    CENTRAL_DEFENDER maxes out at 3 (5-3-2, 5-4-1, 5-2-3), WINGER at 2
    (every formation that uses wingers uses exactly two)."""
    maximums: dict = {}
    for formation in FORMATIONS:
        for position, count in formation.positions.items():
            maximums[position] = max(maximums.get(position, 0), count)
    return maximums


def build_policy(training_type, matches_per_week=DEFAULT_MATCHES_PER_WEEK):
    """Derives a TrainingPriorityPolicy purely from the shape of the
    catalog's TrainingDefinition for `training_type`:

    1. Any position whose best achievable effect *strictly exceeds*
       what the training's blanket "everyone who plays" effect already
       gives is a position the wizard should let the manager select
       explicitly (it's a genuine, targeted capacity slot).
    2. If no position clears that bar, the training is effectively
       team-wide or broadly diffuse -- TEAM_WIDE when the blanket
       reaches FULL (everyone gets the strongest effect just by
       playing), BROAD_PARTICIPATION otherwise (a real but modest
       effect with no positional targeting at all).
    3. Otherwise, positions are grouped by their shared best-effect
       tier. A single qualifying position -> SINGLE_POSITION. Several
       positions all at the same tier -> FIXED_POSITIONAL_CAPACITY.
       Several positions split across multiple tiers (e.g. a FULL group
       and a separate REDUCED group) -> MULTI_EFFECT_POSITIONAL_CAPACITY.

    Per-match capacity for a tier is the sum of each of its positions'
    maximum legal count across every canonical formation; weekly
    capacity multiplies that by `matches_per_week` (two recorded
    matches by default), matching how the Planner already tracks
    weekly coverage.
    """
    definition = definition_for(training_type)
    if definition is None:
        return None

    has_blanket = bool(definition.all_playing_effect)
    blanket_best = (
        best_effect(definition.all_playing_effect.values())
        if has_blanket
        else TrainingEffect.NONE
    )

    positional_positions = tuple(
        position
        for position in definition.position_effects
        if definition.best_effect_for_position(position).sort_order < blanket_best.sort_order
    )

    if not positional_positions:
        policy_type = (
            TrainingPolicyType.TEAM_WIDE
            if blanket_best == TrainingEffect.FULL
            else TrainingPolicyType.BROAD_PARTICIPATION
        )
        return TrainingPriorityPolicy(
            training_type=definition.training_type,
            policy_type=policy_type,
            capacity_groups=(),
            matches_per_week=matches_per_week,
        )

    tiers = sorted(
        {definition.best_effect_for_position(p) for p in positional_positions},
        key=lambda effect: effect.sort_order,
    )

    if len(positional_positions) == 1:
        policy_type = TrainingPolicyType.SINGLE_POSITION
    elif len(tiers) > 1:
        policy_type = TrainingPolicyType.MULTI_EFFECT_POSITIONAL_CAPACITY
    else:
        policy_type = TrainingPolicyType.FIXED_POSITIONAL_CAPACITY

    maximums = formation_position_maximums()
    groups = []
    for tier in tiers:
        tier_positions = tuple(
            sorted(
                (p for p in positional_positions if definition.best_effect_for_position(p) == tier),
                key=lambda p: p.value,
            )
        )
        per_match = sum(maximums.get(position, 0) for position in tier_positions)
        groups.append(
            CapacityGroup(
                effect=tier,
                positions=tier_positions,
                per_match_capacity=per_match,
                weekly_capacity=per_match * matches_per_week,
            )
        )

    return TrainingPriorityPolicy(
        training_type=definition.training_type,
        policy_type=policy_type,
        capacity_groups=tuple(groups),
        matches_per_week=matches_per_week,
    )
