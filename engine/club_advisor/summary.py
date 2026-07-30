from __future__ import annotations

from engine.club_advisor.enums import DepthStatus
from engine.club_advisor.models import (
    DepthSummary,
    PositionDepth,
    SportingSummary,
    SquadSummary,
    TrainingSummary,
)
from engine.squad_intelligence.enums import RecommendedRole, TrainingFit, TrainingPotential
from engine.weekly_training.models import TrainingPriority
from models.position import Position

_ROTATION_ROLES = (
    RecommendedRole.STARTER,
    RecommendedRole.USEFUL_ROTATION,
    RecommendedRole.TACTICAL_SPECIALIST,
)
_DEVELOPMENT_ROLES = (
    RecommendedRole.PRIMARY_TRAINEE,
    RecommendedRole.SECONDARY_TRAINEE,
    RecommendedRole.DEVELOPMENT_PROJECT,
)

_ATTACKING_POSITIONS = ("WINGER", "FORWARD")
_MIDFIELD_POSITIONS = ("INNER_MIDFIELDER",)
_DEFENSIVE_POSITIONS = ("CENTRAL_DEFENDER", "WING_BACK")

# Configurable depth-status thresholds -- documented here rather than as
# magic numbers scattered through rules.
_NO_REPLACEMENT_MAX = 1
_ONE_REPLACEMENT_MAX = 2
_HEALTHY_COMPETITION_MAX = 4
_FUTURE_SHORTAGE_AGE_THRESHOLD = 29


def build_training_summary(context) -> TrainingSummary:
    priority_rows = getattr(context, "training_priority_rows", ()) or ()
    if priority_rows:
        required_100 = sum(
            1 for row in priority_rows
            if getattr(row, "priority", None) == TrainingPriority.REQUIRED_100
        )
        required_50 = sum(
            1 for row in priority_rows
            if getattr(row, "priority", None) == TrainingPriority.REQUIRED_50
        )
        return TrainingSummary(
            active_training_type=context.active_training_type,
            primary_trainee_count=required_100,
            secondary_trainee_count=required_50,
            players_without_training=max(
                0,
                len(priority_rows) - required_100 - required_50,
            ),
            total_players_evaluated=len(priority_rows),
        )

    reports = context.squad_reports
    primary = sum(1 for r in reports if r.recommended_role == RecommendedRole.PRIMARY_TRAINEE)
    secondary = sum(1 for r in reports if r.recommended_role == RecommendedRole.SECONDARY_TRAINEE)
    without_training = sum(
        1 for r in reports if r.training_fit in (TrainingFit.NO_TRAINING, TrainingFit.UNKNOWN)
    )
    full_effect = sum(1 for r in reports if r.training_fit == TrainingFit.EXCELLENT)
    reduced_effect = sum(1 for r in reports if r.training_fit == TrainingFit.COMPATIBLE)

    return TrainingSummary(
        active_training_type=context.active_training_type,
        primary_trainee_count=primary,
        secondary_trainee_count=secondary,
        players_without_training=without_training,
        full_effect_slots_used=full_effect,
        reduced_effect_slots_used=reduced_effect,
        total_players_evaluated=len(reports),
    )


_PROJECT_TRAINING_FITS = (TrainingFit.EXCELLENT, TrainingFit.COMPATIBLE, TrainingFit.PARTIAL)
_PROJECT_TRAINING_POTENTIALS = (
    TrainingPotential.MEDIUM, TrainingPotential.HIGH, TrainingPotential.VERY_HIGH,
)


def _is_training_project(report) -> bool:
    """A player is a development "project" whenever they're
    genuinely being developed under the active training -- this is
    independent of their current recommended_role. A player can be
    both a STARTER right now *and* a project for a future position
    (the sprint's own example: current best position Wing Back, future
    project Playmaking trainee) -- these are not mutually exclusive,
    even though `recommended_role` only ever picks one primary label."""
    return (
        report.training_fit in _PROJECT_TRAINING_FITS
        and report.training_potential in _PROJECT_TRAINING_POTENTIALS
    )


def build_squad_summary(context) -> SquadSummary:
    reports = context.squad_reports

    def _select(roles):
        return tuple(r.player_name for r in reports if r.recommended_role in roles)

    project_players = tuple(r.player_name for r in reports if _is_training_project(r))
    key_starter_players = _select((RecommendedRole.KEY_STARTER,))
    rotation_players = _select(_ROTATION_ROLES)
    transfer_candidate_players = _select((RecommendedRole.TRANSFER_CANDIDATE,))
    replaceable_players = _select((RecommendedRole.REPLACEABLE,))
    veteran_players = _select((RecommendedRole.VETERAN_MENTOR,))
    depth_players = _select((RecommendedRole.DEPTH_PLAYER,))

    return SquadSummary(
        key_starter_count=len(key_starter_players),
        rotation_count=len(rotation_players),
        development_project_count=len(project_players),
        transfer_candidate_count=len(transfer_candidate_players),
        replaceable_count=len(replaceable_players),
        veteran_count=len(veteran_players),
        depth_player_count=len(depth_players),
        key_starter_players=key_starter_players,
        rotation_players=rotation_players,
        development_project_players=project_players,
        transfer_candidate_players=transfer_candidate_players,
        replaceable_players=replaceable_players,
        veteran_players=veteran_players,
        depth_players=depth_players,
    )


def _depth_status_for(position_value, count, squad_context) -> DepthStatus:
    if count <= _NO_REPLACEMENT_MAX:
        return DepthStatus.NO_REPLACEMENT
    if count <= _ONE_REPLACEMENT_MAX:
        ages = _ages_at_position(position_value, squad_context)
        if ages and (sum(ages) / len(ages)) >= _FUTURE_SHORTAGE_AGE_THRESHOLD:
            return DepthStatus.FUTURE_SHORTAGE
        return DepthStatus.ONE_REPLACEMENT
    if count <= _HEALTHY_COMPETITION_MAX:
        return DepthStatus.HEALTHY_COMPETITION
    return DepthStatus.EXCESS_PLAYERS


def _ages_at_position(position_value, squad_context):
    if squad_context is None:
        return ()
    return tuple(getattr(squad_context, "ages_by_position", {}).get(position_value, ()))


def build_depth_summary(context) -> DepthSummary:
    squad_context = context.squad_context
    positional_depth = getattr(squad_context, "positional_depth", {}) if squad_context else {}

    positions = []
    for position in Position:
        count = positional_depth.get(position.value, 0)
        status = _depth_status_for(position.value, count, squad_context)
        temporary_count = None
        temporary_status = ""
        if squad_context is not None and hasattr(squad_context, "temporary_depth_at"):
            temporary_count = squad_context.temporary_depth_at(position.value)
            temporary_status = _depth_status_for(
                position.value, temporary_count, squad_context
            ).value
        positions.append(
            PositionDepth(
                position=position.value,
                status=status.value,
                player_count=count,
                temporary_count=temporary_count,
                temporary_status=temporary_status,
            )
        )
    return DepthSummary(positions=tuple(positions))


def build_sporting_summary(depth_summary: DepthSummary) -> SportingSummary:
    depth_by_position = {item.position: item for item in depth_summary.positions}
    observations = []

    def _group_status(position_group):
        counts = [depth_by_position[p].player_count for p in position_group if p in depth_by_position]
        return sum(counts)

    if _group_status(_MIDFIELD_POSITIONS) <= 1:
        observations.append("club_advisor.sporting.midfield_concentrated")
    if _group_status(_ATTACKING_POSITIONS) <= 2:
        observations.append("club_advisor.sporting.attack_relies_on_few_players")
    if _group_status(_DEFENSIVE_POSITIONS) <= 2:
        observations.append("club_advisor.sporting.defensive_flexibility_limited")
    if depth_by_position.get("WINGER") and depth_by_position["WINGER"].player_count >= 3:
        observations.append("club_advisor.sporting.wing_depth_acceptable")

    return SportingSummary(observation_keys=tuple(observations))
