from __future__ import annotations

from dataclasses import asdict, dataclass, field

from engine.analyzers.team_rater import TeamRater
from engine.calculators.chance_distribution_calculator import (
    ChanceDistributionCalculator,
)
from engine.evaluators.match_evaluator import MatchEvaluator
from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator,
)
from engine.optimizers.tactic_optimizer import TacticOptimizer
from engine.ratings.rating_scale_normalizer import (
    RatingScaleNormalizer,
    rating_scale_of,
)
from models.rating_scale import RatingScale
from models.tactic import Tactic


DEFAULT_RATING_NORMALIZER = RatingScaleNormalizer()


TACTICAL_TIE_TOLERANCE = 0.01
TRAINING_TIEBREAKER_WEIGHT = 0.0025


@dataclass(frozen=True)
class ObjectiveComponents:
    lineup_positional_score: float
    possession_component: float
    attack_matchup_component: float
    defense_matchup_component: float
    expected_goals: float
    opponent_expected_goals: float
    win_probability: float
    draw_probability: float
    loss_probability: float
    training_component: float = 0.0
    availability_component: float = 0.0
    final_objective_score: float = 0.0


@dataclass(frozen=True)
class LineupObjectiveTrace:
    candidate_id: str
    sector_ratings: dict[str, float]
    opponent_ratings: dict[str, float]
    tactic: str
    tactic_level: float
    route_weights: dict[str, float]
    components: ObjectiveComponents
    lineup: tuple[dict[str, str], ...] = field(default_factory=tuple)
    raw_internal_ratings: dict[str, float] = field(default_factory=dict)
    normalized_ht_ratings: dict[str, float] = field(default_factory=dict)
    opponent_ht_ratings: dict[str, float] = field(default_factory=dict)
    calibration_version: str = ""
    calibration_confidence: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class SectorDelta:
    sector: str
    value: float
    relevance: str
    reason: str


@dataclass(frozen=True)
class LineupComparisonResult:
    candidate_a: LineupObjectiveTrace
    candidate_b: LineupObjectiveTrace
    sector_deltas: tuple[SectorDelta, ...]
    possession_delta: float
    offensive_matchup_delta: float
    defensive_matchup_delta: float
    expected_scoring_impact: float
    expected_concession_impact: float
    training_impact: float
    preferred_candidate_id: str
    final_tactical_preference: str
    confidence: str
    summary: str
    explanation: str

    def to_dict(self):
        return asdict(self)


class LineupObjectiveEvaluator:
    @classmethod
    def build_trace(
        cls,
        ratings,
        opponent_ratings,
        match_evaluation,
        probabilities,
        tactic=Tactic.NORMAL,
        tactic_level=0.0,
        route_weights=None,
        lineup=None,
        training_score=0.0,
        availability_penalty=0.0,
        candidate_id=None,
        raw_internal_ratings=None,
        normalized_ht_ratings=None,
        opponent_ht_ratings=None,
        calibration_version="",
        calibration_confidence="",
    ):
        tactic = _coerce_tactic(tactic)
        if route_weights is None:
            route_weights = ChanceDistributionCalculator.calculate(tactic)

        sectors = _ratings_to_dict(ratings)
        opponent = _ratings_to_dict(opponent_ratings)
        provenance = getattr(ratings, "provenance", None)
        if not calibration_version and provenance is not None:
            calibration_version = getattr(
                provenance,
                "calibration_version",
                "",
            )
        if not calibration_confidence and provenance is not None:
            confidence = getattr(provenance, "confidence", "")
            calibration_confidence = getattr(
                confidence,
                "value",
                str(confidence or ""),
            )
        tactical_score = float(probabilities.win)
        final_score = (
            tactical_score
            + TRAINING_TIEBREAKER_WEIGHT * float(training_score or 0.0)
            - float(availability_penalty or 0.0)
        )
        components = ObjectiveComponents(
            lineup_positional_score=sum(sectors.values()),
            possession_component=float(match_evaluation.chance_probability),
            attack_matchup_component=float(match_evaluation.expected_goals),
            defense_matchup_component=-float(
                match_evaluation.opponent_expected_goals
            ),
            expected_goals=float(match_evaluation.expected_goals),
            opponent_expected_goals=float(
                match_evaluation.opponent_expected_goals
            ),
            win_probability=float(probabilities.win),
            draw_probability=float(probabilities.draw),
            loss_probability=float(probabilities.loss),
            training_component=float(training_score or 0.0),
            availability_component=-float(availability_penalty or 0.0),
            final_objective_score=final_score,
        )

        return LineupObjectiveTrace(
            candidate_id=candidate_id or _candidate_id(lineup, sectors),
            sector_ratings=sectors,
            opponent_ratings=opponent,
            raw_internal_ratings=(
                _ratings_to_dict(raw_internal_ratings)
                if raw_internal_ratings is not None
                else {}
            ),
            normalized_ht_ratings=(
                _ratings_to_dict(normalized_ht_ratings)
                if normalized_ht_ratings is not None
                else sectors
            ),
            opponent_ht_ratings=(
                _ratings_to_dict(opponent_ht_ratings)
                if opponent_ht_ratings is not None
                else opponent
            ),
            calibration_version=calibration_version,
            calibration_confidence=calibration_confidence,
            tactic=tactic.value,
            tactic_level=float(tactic_level or 0.0),
            route_weights={
                "left": float(route_weights.left),
                "center": float(route_weights.center),
                "right": float(route_weights.right),
            },
            components=components,
            lineup=_lineup_to_tuple(lineup),
        )

    @classmethod
    def evaluate_lineup(
        cls,
        lineup,
        opponent_ratings,
        tactic=Tactic.NORMAL,
        training_score=0.0,
        availability_penalty=0.0,
        candidate_id=None,
        config=None,
    ):
        ratings = TeamRater.calculate(lineup)
        return cls.evaluate_ratings(
            ratings,
            opponent_ratings,
            tactic=tactic,
            lineup=lineup,
            training_score=training_score,
            availability_penalty=availability_penalty,
            candidate_id=candidate_id,
            config=config,
        )

    @classmethod
    def evaluate_ratings(
        cls,
        ratings,
        opponent_ratings,
        tactic=Tactic.NORMAL,
        lineup=None,
        training_score=0.0,
        availability_penalty=0.0,
        candidate_id=None,
        config=None,
    ):
        tactic = _coerce_tactic(tactic)
        raw_internal_ratings = None
        normalized_ht_ratings = None
        opponent_ht_ratings = None
        calibration_version = ""
        calibration_confidence = ""

        if (
            rating_scale_of(ratings) != RatingScale.UNKNOWN
            or rating_scale_of(opponent_ratings) != RatingScale.UNKNOWN
        ):
            calibrated, opponent_ratings = DEFAULT_RATING_NORMALIZER.normalize_matchup(
                ratings,
                opponent_ratings,
            )
            raw_internal_ratings = calibrated.raw_internal_ratings
            normalized_ht_ratings = calibrated.ratings
            opponent_ht_ratings = opponent_ratings
            calibration_version = calibrated.calibration_version
            calibration_confidence = calibrated.confidence.value
            ratings = calibrated.ratings

        if lineup is not None:
            context, effects, evaluation, probabilities = (
                TacticOptimizer._evaluate(
                    ratings,
                    tactic,
                    opponent_ratings,
                    lineup=lineup,
                    config=config,
                )
            )
            effective_ratings = effects.ratings
            route_weights = effects.our_distribution
            tactic_level = float(context.level)
        else:
            tactic_level = 0.0
            route_weights = ChanceDistributionCalculator.calculate(tactic)
            evaluation = MatchEvaluator.evaluate(
                ratings,
                opponent_ratings,
                tactic=tactic,
                our_distribution=route_weights,
                config=config,
            )
            probabilities = ResultProbabilityEvaluator.evaluate(
                evaluation.expected_goals,
                evaluation.opponent_expected_goals,
            )
            effective_ratings = ratings

        return cls.build_trace(
            effective_ratings,
            opponent_ratings,
            evaluation,
            probabilities,
            tactic=tactic,
            tactic_level=tactic_level,
            route_weights=route_weights,
            lineup=lineup,
            training_score=training_score,
            availability_penalty=availability_penalty,
            candidate_id=candidate_id,
            raw_internal_ratings=raw_internal_ratings,
            normalized_ht_ratings=normalized_ht_ratings or effective_ratings,
            opponent_ht_ratings=opponent_ht_ratings or opponent_ratings,
            calibration_version=calibration_version,
            calibration_confidence=calibration_confidence,
        )


class HeadToHeadLineupComparator:
    def compare(
        self,
        candidate_a,
        candidate_b,
        opponent_ratings,
        tactic=Tactic.NORMAL,
        training_score_a=0.0,
        training_score_b=0.0,
        confidence="HIGH",
        config=None,
    ):
        trace_a = self._trace(
            candidate_a,
            opponent_ratings,
            tactic,
            training_score_a,
            "A",
            config,
        )
        trace_b = self._trace(
            candidate_b,
            opponent_ratings,
            tactic,
            training_score_b,
            "B",
            config,
        )

        tactical_delta = (
            trace_b.components.win_probability
            - trace_a.components.win_probability
        )
        if abs(tactical_delta) <= TACTICAL_TIE_TOLERANCE:
            preference_delta = (
                trace_b.components.final_objective_score
                - trace_a.components.final_objective_score
            )
            preference_basis = "training tiebreaker"
        else:
            preference_delta = tactical_delta
            preference_basis = "tactical value"

        preferred = trace_b if preference_delta > 0 else trace_a
        rejected = trace_a if preferred is trace_b else trace_b
        sector_deltas = _sector_deltas(trace_a, trace_b)
        summary = _summary_from_deltas(trace_a, trace_b, preferred)
        explanation = _explanation(
            trace_a,
            trace_b,
            preferred,
            rejected,
            sector_deltas,
            preference_basis,
        )

        return LineupComparisonResult(
            candidate_a=trace_a,
            candidate_b=trace_b,
            sector_deltas=sector_deltas,
            possession_delta=(
                trace_b.components.possession_component
                - trace_a.components.possession_component
            ),
            offensive_matchup_delta=(
                trace_b.components.attack_matchup_component
                - trace_a.components.attack_matchup_component
            ),
            defensive_matchup_delta=(
                trace_b.components.defense_matchup_component
                - trace_a.components.defense_matchup_component
            ),
            expected_scoring_impact=(
                trace_b.components.expected_goals
                - trace_a.components.expected_goals
            ),
            expected_concession_impact=(
                trace_b.components.opponent_expected_goals
                - trace_a.components.opponent_expected_goals
            ),
            training_impact=(
                trace_b.components.training_component
                - trace_a.components.training_component
            ),
            preferred_candidate_id=preferred.candidate_id,
            final_tactical_preference=(
                f"{preferred.candidate_id} by {preference_basis}"
            ),
            confidence=confidence,
            summary=summary,
            explanation=explanation,
        )

    @staticmethod
    def _trace(
        candidate,
        opponent_ratings,
        tactic,
        training_score,
        candidate_id,
        config,
    ):
        if hasattr(candidate, "players"):
            return LineupObjectiveEvaluator.evaluate_lineup(
                candidate,
                opponent_ratings,
                tactic=tactic,
                training_score=training_score,
                candidate_id=candidate_id,
                config=config,
            )
        return LineupObjectiveEvaluator.evaluate_ratings(
            candidate,
            opponent_ratings,
            tactic=tactic,
            training_score=training_score,
            candidate_id=candidate_id,
            config=config,
        )


def select_pareto_frontier(traces, max_options=5):
    if not traces:
        return ()

    candidates = []
    selectors = (
        lambda trace: trace.components.possession_component,
        lambda trace: trace.components.attack_matchup_component,
        lambda trace: -trace.components.opponent_expected_goals,
        lambda trace: trace.components.final_objective_score,
    )
    for selector in selectors:
        best = max(traces, key=selector)
        if best not in candidates:
            candidates.append(best)

    candidates.sort(
        key=lambda trace: trace.components.final_objective_score,
        reverse=True,
    )
    return tuple(candidates[:max_options])


def _coerce_tactic(value):
    if isinstance(value, Tactic):
        return value
    for tactic in Tactic:
        if value in {tactic.value, tactic.name}:
            return tactic
    return Tactic.NORMAL


def _ratings_to_dict(ratings):
    return {
        "left_defense": float(getattr(ratings, "left_defense", 0.0) or 0.0),
        "central_defense": float(
            getattr(ratings, "central_defense", 0.0) or 0.0
        ),
        "right_defense": float(
            getattr(ratings, "right_defense", 0.0) or 0.0
        ),
        "midfield": float(getattr(ratings, "midfield", 0.0) or 0.0),
        "left_attack": float(getattr(ratings, "left_attack", 0.0) or 0.0),
        "central_attack": float(
            getattr(ratings, "central_attack", 0.0) or 0.0
        ),
        "right_attack": float(
            getattr(ratings, "right_attack", 0.0) or 0.0
        ),
    }


def _candidate_id(lineup, sectors):
    if lineup is None:
        return "ratings:" + ",".join(
            f"{key}={value:.2f}" for key, value in sorted(sectors.items())
        )
    return "lineup:" + "|".join(
        sorted(
            f"{getattr(player.player, 'name', '')}:"
            f"{player.position.value}:{player.side.value}"
            for player in lineup.players
        )
    )


def _lineup_to_tuple(lineup):
    if lineup is None:
        return ()
    return tuple(
        {
            "player": getattr(lineup_player.player, "name", ""),
            "position": lineup_player.position.value,
            "side": lineup_player.side.value,
            "order": getattr(lineup_player.order, "value", ""),
            "order_side": getattr(lineup_player.order_side, "value", ""),
        }
        for lineup_player in lineup.players
    )


def _sector_deltas(trace_a, trace_b):
    result = []
    for sector, value_b in trace_b.sector_ratings.items():
        value_a = trace_a.sector_ratings.get(sector, 0.0)
        delta = value_b - value_a
        if abs(delta) < 0.0001:
            continue
        result.append(
            SectorDelta(
                sector=sector,
                value=delta,
                relevance=_sector_relevance(sector, trace_b),
                reason=_sector_reason(sector, delta, trace_b),
            )
        )
    return tuple(result)


def _sector_relevance(sector, trace):
    if sector == "midfield":
        gap = (
            trace.sector_ratings["midfield"]
            - trace.opponent_ratings["midfield"]
        )
        return "high" if abs(gap) <= 3.0 else "medium"
    if "attack" in sector:
        route = _route_for_sector(sector)
        return "high" if trace.route_weights[route] >= 0.28 else "medium"
    if "defense" in sector:
        opponent_attack = _opponent_attack_for_defense(sector, trace)
        our_defense = trace.sector_ratings[sector]
        return "high" if opponent_attack >= our_defense else "medium"
    return "medium"


def _sector_reason(sector, delta, trace):
    direction = "improves" if delta > 0 else "sacrifices"
    if sector == "midfield":
        return (
            f"{direction} chance control against opponent midfield "
            f"{trace.opponent_ratings['midfield']:.2f}."
        )
    if "attack" in sector:
        route = _route_for_sector(sector)
        return (
            f"{direction} the {route} attacking route, weighted "
            f"{trace.route_weights[route]:.2f} by the selected tactic."
        )
    if "defense" in sector:
        return (
            f"{direction} protection against that opponent attacking channel."
        )
    return f"{direction} {sector.replace('_', ' ')}."


def _route_for_sector(sector):
    if sector.startswith("left"):
        return "left"
    if sector.startswith("right"):
        return "right"
    return "center"


def _opponent_attack_for_defense(sector, trace):
    if sector == "left_defense":
        return trace.opponent_ratings["right_attack"]
    if sector == "right_defense":
        return trace.opponent_ratings["left_attack"]
    return trace.opponent_ratings["central_attack"]


def _summary_from_deltas(trace_a, trace_b, preferred):
    midfield_delta = (
        trace_b.sector_ratings["midfield"]
        - trace_a.sector_ratings["midfield"]
    )
    xg_delta = (
        trace_b.components.expected_goals
        - trace_a.components.expected_goals
    )
    oxg_delta = (
        trace_b.components.opponent_expected_goals
        - trace_a.components.opponent_expected_goals
    )
    if preferred is trace_b and midfield_delta > 0.5:
        return "Prioridad: dominar el mediocampo."
    if oxg_delta < -0.15:
        return "Prioridad: reducir el riesgo defensivo."
    if xg_delta > 0.15:
        return "Prioridad: aumentar la produccion ofensiva."
    return "Prioridad: elegir el mejor balance tactico."


def _explanation(
    trace_a,
    trace_b,
    preferred,
    rejected,
    sector_deltas,
    preference_basis,
):
    deltas = [
        f"{delta.sector.replace('_', ' ').title()}: {delta.value:+.2f} HT"
        for delta in sector_deltas[:7]
    ]
    deltas_text = "; ".join(deltas) if deltas else "sin cambios sectoriales"
    return (
        f"{preferred.candidate_id} es preferido sobre "
        f"{rejected.candidate_id} por {preference_basis}. "
        f"Impacto sectorial B vs A: {deltas_text}. "
        f"Posesion: "
        f"{trace_b.components.possession_component - trace_a.components.possession_component:+.3f}; "
        f"xG: "
        f"{trace_b.components.expected_goals - trace_a.components.expected_goals:+.2f}; "
        f"xG rival: "
        f"{trace_b.components.opponent_expected_goals - trace_a.components.opponent_expected_goals:+.2f}; "
        f"entrenamiento: "
        f"{trace_b.components.training_component - trace_a.components.training_component:+.2f}."
    )
