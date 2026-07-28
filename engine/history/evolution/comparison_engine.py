from __future__ import annotations

from engine.history.evolution.comparison_metrics import (
    absolute_delta,
    percentage_delta,
    safe_average,
)
from engine.history.evolution.comparison_models import (
    DEFAULT_TREND_THRESHOLDS,
    SectorEvolution,
    Trend,
    TrendThresholds,
    classify_trend,
)
from engine.history.evolution.comparison_result import (
    FormationEvolution,
    HistoricalEvolutionResult,
    LineupChangeStatus,
    LineupEvolution,
    LineupPlayerChange,
    MetricDelta,
    OverallEvolution,
    PredictionEvolution,
    TacticalEvolution,
)
from engine.history.evolution.comparison_selector import (
    select_custom,
    select_previous_cup_match,
    select_previous_friendly,
    select_previous_league_match,
    select_previous_match,
    select_previous_same_cohort,
)
from engine.history.evolution.comparison_validation import ensure_comparable

# The seven sectors this sprint reports on, in the order specified by
# the Historical Evolution Engine brief. (indirect_defense/indirect_attack
# exist on SectorRatings but are intentionally out of scope here.)
REPORTED_SECTORS = (
    "midfield",
    "right_defense",
    "central_defense",
    "left_defense",
    "right_attack",
    "central_attack",
    "left_attack",
)


def _player_key(entry) -> str:
    """Stable identity for matching a lineup entry across snapshots.
    Prefers player_id; falls back to a normalized player_name, since the
    current snapshot factory doesn't always populate player_id yet.
    Never matches by row position."""
    player_id = (entry.player_id or "").strip()
    if player_id:
        return f"id:{player_id}"
    return f"name:{entry.player_name.strip().casefold()}"


def compare_sectors(
    previous_ratings,
    current_ratings,
    thresholds: TrendThresholds | None = None,
) -> tuple[SectorEvolution, ...]:
    sectors = []
    for sector in REPORTED_SECTORS:
        previous_value = getattr(previous_ratings, sector, None) if previous_ratings else None
        current_value = getattr(current_ratings, sector, None) if current_ratings else None
        delta = absolute_delta(previous_value, current_value)
        pct = percentage_delta(previous_value, current_value)
        sectors.append(
            SectorEvolution(
                sector=sector,
                previous_value=previous_value,
                current_value=current_value,
                absolute_delta=delta,
                percentage_delta=pct,
                trend=classify_trend(pct, thresholds),
            )
        )
    return tuple(sectors)


def compare_overall(
    sectors: tuple[SectorEvolution, ...],
    thresholds: TrendThresholds | None = None,
) -> OverallEvolution:
    comparable = [sector for sector in sectors if sector.absolute_delta is not None]

    overall_rating_delta = (
        sum(sector.absolute_delta for sector in comparable) if comparable else None
    )
    average_sector_delta = safe_average(sector.percentage_delta for sector in sectors)

    improved = sum(
        1 for sector in sectors
        if sector.trend in (Trend.IMPROVEMENT, Trend.MAJOR_IMPROVEMENT)
    )
    declined = sum(
        1 for sector in sectors
        if sector.trend in (Trend.DECLINE, Trend.MAJOR_DECLINE)
    )
    unchanged = len(sectors) - improved - declined

    ranked = [
        sector for sector in sectors if sector.percentage_delta is not None
    ]
    best_improved_sector = (
        max(ranked, key=lambda sector: sector.percentage_delta).sector
        if ranked
        else None
    )
    worst_sector = (
        min(ranked, key=lambda sector: sector.percentage_delta).sector
        if ranked
        else None
    )

    return OverallEvolution(
        overall_rating_delta=overall_rating_delta,
        average_sector_delta=average_sector_delta,
        best_improved_sector=best_improved_sector,
        worst_sector=worst_sector,
        improved_sector_count=improved,
        declined_sector_count=declined,
        unchanged_sector_count=unchanged,
        overall_trend=classify_trend(average_sector_delta, thresholds),
    )


def compare_formation(previous_tactical, current_tactical) -> FormationEvolution:
    previous_formation = previous_tactical.formation if previous_tactical else ""
    current_formation = current_tactical.formation if current_tactical else ""
    return FormationEvolution(
        previous_formation=previous_formation,
        current_formation=current_formation,
        changed=previous_formation != current_formation,
    )


def compare_tactical(previous_tactical, current_tactical) -> TacticalEvolution:
    previous_tactic = previous_tactical.selected_tactic if previous_tactical else ""
    current_tactic = current_tactical.selected_tactic if current_tactical else ""
    previous_level = previous_tactical.tactic_level if previous_tactical else None
    current_level = current_tactical.tactic_level if current_tactical else None
    previous_attitude = previous_tactical.team_attitude if previous_tactical else ""
    current_attitude = current_tactical.team_attitude if current_tactical else ""
    previous_confidence = previous_tactical.confidence if previous_tactical else ""
    current_confidence = current_tactical.confidence if current_tactical else ""
    return TacticalEvolution(
        previous_tactic=previous_tactic,
        current_tactic=current_tactic,
        tactic_changed=previous_tactic != current_tactic,
        previous_tactic_level=previous_level,
        current_tactic_level=current_level,
        tactic_level_delta=absolute_delta(previous_level, current_level),
        previous_attitude=previous_attitude,
        current_attitude=current_attitude,
        attitude_changed=previous_attitude != current_attitude,
        previous_confidence=previous_confidence,
        current_confidence=current_confidence,
        confidence_changed=previous_confidence != current_confidence,
    )


def compare_lineup(previous_lineup, current_lineup) -> LineupEvolution:
    previous_lineup = previous_lineup or ()
    current_lineup = current_lineup or ()

    previous_by_key = {}
    for entry in previous_lineup:
        previous_by_key.setdefault(_player_key(entry), entry)

    current_by_key = {}
    for entry in current_lineup:
        current_by_key.setdefault(_player_key(entry), entry)

    changes = []

    for key, current_entry in current_by_key.items():
        previous_entry = previous_by_key.get(key)
        if previous_entry is None:
            changes.append(
                LineupPlayerChange(
                    player_id=current_entry.player_id,
                    player_name=current_entry.player_name,
                    status=LineupChangeStatus.ADDED,
                    current_position=current_entry.position,
                    current_order=current_entry.individual_order,
                    current_order_side=current_entry.order_side,
                    current_number=current_entry.number,
                )
            )
            continue

        changes.append(
            LineupPlayerChange(
                player_id=current_entry.player_id or previous_entry.player_id,
                player_name=current_entry.player_name,
                status=LineupChangeStatus.KEPT,
                previous_position=previous_entry.position,
                current_position=current_entry.position,
                position_changed=previous_entry.position != current_entry.position,
                previous_order=previous_entry.individual_order,
                current_order=current_entry.individual_order,
                order_changed=(
                    previous_entry.individual_order != current_entry.individual_order
                ),
                previous_order_side=previous_entry.order_side,
                current_order_side=current_entry.order_side,
                order_side_changed=(
                    previous_entry.order_side != current_entry.order_side
                ),
                previous_number=previous_entry.number,
                current_number=current_entry.number,
                number_changed=previous_entry.number != current_entry.number,
            )
        )

    for key, previous_entry in previous_by_key.items():
        if key in current_by_key:
            continue
        changes.append(
            LineupPlayerChange(
                player_id=previous_entry.player_id,
                player_name=previous_entry.player_name,
                status=LineupChangeStatus.REMOVED,
                previous_position=previous_entry.position,
                previous_order=previous_entry.individual_order,
                previous_order_side=previous_entry.order_side,
                previous_number=previous_entry.number,
            )
        )

    return LineupEvolution(changes=tuple(changes))


def compare_prediction(previous_prediction, current_prediction) -> PredictionEvolution:
    def _metric(attribute):
        previous_value = getattr(previous_prediction, attribute, None) if previous_prediction else None
        current_value = getattr(current_prediction, attribute, None) if current_prediction else None
        return MetricDelta(
            previous=previous_value,
            current=current_value,
            delta=absolute_delta(previous_value, current_value),
        )

    return PredictionEvolution(
        expected_goals=_metric("expected_goals"),
        opponent_expected_goals=_metric("opponent_expected_goals"),
        win_probability=_metric("win_probability"),
        draw_probability=_metric("draw_probability"),
        loss_probability=_metric("loss_probability"),
        possession=_metric("possession"),
    )


def evolution_score(overall: OverallEvolution) -> float:
    """A single deterministic summary number, NOT a rating. Formula:
    average sector percentage delta, scaled down by a factor of 10 and
    rounded to 2 decimals (a +4.2% average sector improvement becomes
    an evolution score of +0.42). Zero when there's nothing comparable."""
    if overall.average_sector_delta is None:
        return 0.0
    return round(overall.average_sector_delta / 10.0, 2)


def compare(
    current,
    previous,
    thresholds: TrendThresholds | None = None,
) -> HistoricalEvolutionResult:
    """Pure, deterministic comparison of two historical snapshots. No
    AI, no heuristics — every field is either a straight delta or a
    threshold-based classification of one."""
    ensure_comparable(current, previous)
    thresholds = thresholds or DEFAULT_TREND_THRESHOLDS

    sectors = compare_sectors(
        previous.predictions.ratings if previous.predictions else None,
        current.predictions.ratings if current.predictions else None,
        thresholds,
    )
    overall = compare_overall(sectors, thresholds)

    result = HistoricalEvolutionResult(
        current_snapshot_id=current.snapshot_id,
        previous_snapshot_id=previous.snapshot_id,
        overall=overall,
        sectors=sectors,
        formation=compare_formation(previous.tactical_setup, current.tactical_setup),
        tactical=compare_tactical(previous.tactical_setup, current.tactical_setup),
        lineup=compare_lineup(previous.lineup, current.lineup),
        prediction=compare_prediction(previous.predictions, current.predictions),
        evolution_score=0.0,
    )
    return _with_evolution_score(result)


def _with_evolution_score(result: HistoricalEvolutionResult) -> HistoricalEvolutionResult:
    from dataclasses import replace

    return replace(result, evolution_score=evolution_score(result.overall))


class HistoricalEvolutionEngine:
    """Convenience facade bundling comparison + previous-match selection
    (Comparison Policies) together, matching the service API requested
    for this sprint. Every method returns None (not an error) when no
    eligible previous snapshot is found among the candidates — there's
    simply nothing to compare against yet."""

    def __init__(self, thresholds: TrendThresholds | None = None):
        self.thresholds = thresholds or DEFAULT_TREND_THRESHOLDS

    def compare(self, current, previous) -> HistoricalEvolutionResult:
        return compare(current, previous, self.thresholds)

    def compare_with_previous(self, current, candidates, *, include_planned=False):
        previous = select_previous_match(
            current, candidates, include_planned=include_planned
        )
        if previous is None:
            return None
        return self.compare(current, previous)

    def compare_with_previous_league(self, current, candidates, *, include_planned=False):
        previous = select_previous_league_match(
            current, candidates, include_planned=include_planned
        )
        if previous is None:
            return None
        return self.compare(current, previous)

    def compare_with_previous_cup(self, current, candidates, *, include_planned=False):
        previous = select_previous_cup_match(
            current, candidates, include_planned=include_planned
        )
        if previous is None:
            return None
        return self.compare(current, previous)

    def compare_with_previous_friendly(self, current, candidates, *, include_planned=False):
        previous = select_previous_friendly(
            current, candidates, include_planned=include_planned
        )
        if previous is None:
            return None
        return self.compare(current, previous)

    def compare_same_cohort(self, current, candidates, *, include_planned=False):
        previous = select_previous_same_cohort(
            current, candidates, include_planned=include_planned
        )
        if previous is None:
            return None
        return self.compare(current, previous)

    def compare_custom(
        self,
        current,
        candidates,
        *,
        competition_type=None,
        team_type=None,
        same_cohort=False,
        include_planned=False,
    ):
        previous = select_custom(
            current,
            candidates,
            competition_type=competition_type,
            team_type=team_type,
            same_cohort=same_cohort,
            include_planned=include_planned,
        )
        if previous is None:
            return None
        return self.compare(current, previous)
