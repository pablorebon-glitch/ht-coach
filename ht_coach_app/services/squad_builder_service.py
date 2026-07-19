from dataclasses import dataclass, field

from engine.analyzers.formation_analyzer import FormationAnalyzer
from engine.optimizers.formation_optimizer import FormationOptimizer
from ht_coach_app.core.localization import t
from ht_coach_app.core.position_formatting import format_position
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    TeamRatingsResult,
)
from models.formations import FORMATION_BY_NAME


AUTO_FORMATION = "Auto"


@dataclass(frozen=True)
class FormationRankingResult:
    formation_name: str
    overall_score: float
    score_delta: float
    confidence: str
    reason: str
    midfield: float = 0.0
    attack: float = 0.0
    defense: float = 0.0
    experience: float | None = None
    is_best: bool = False
    is_selected: bool = False


@dataclass(frozen=True)
class TeamProfileResult:
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    preferred_style: str = ""


@dataclass(frozen=True)
class IdealXIResult:
    mode: str
    selected_formation_name: str
    best_formation_name: str
    overall_score: float
    confidence: str
    reason: str
    rankings: list[FormationRankingResult] = field(default_factory=list)
    formations: list[FormationAnalysisResult] = field(default_factory=list)
    selected_formation: FormationAnalysisResult | None = None
    team_profile: TeamProfileResult = field(default_factory=TeamProfileResult)


class SquadBuilderService:
    def __init__(self, optimizer=FormationOptimizer.optimize):
        self._optimizer = optimizer

    def supported_formations(self):
        return list(FORMATION_BY_NAME.keys())

    def selection_options(self):
        return [AUTO_FORMATION] + self.supported_formations()

    def build(self, players, formation_name=AUTO_FORMATION):
        engine_results = self._optimizer(
            players,
            list(FORMATION_BY_NAME.values()),
        )

        if not engine_results:
            return IdealXIResult(
                mode=formation_name or AUTO_FORMATION,
                selected_formation_name="",
                best_formation_name="",
                overall_score=0.0,
                confidence=t("squad_builder.confidence.low"),
                reason=t("squad_builder.reason.empty"),
            )

        best = engine_results[0]
        best_name = best[0].name
        requested_name = str(formation_name or AUTO_FORMATION)
        selected_name = (
            best_name
            if requested_name == AUTO_FORMATION
            else requested_name
        )

        if selected_name not in FORMATION_BY_NAME:
            selected_name = best_name
            requested_name = AUTO_FORMATION

        best_score = float(best[3])
        results_by_name = {
            formation.name: (formation, lineup, ratings, float(score))
            for formation, lineup, ratings, score in engine_results
        }
        selected = results_by_name[selected_name]
        selected_score = float(selected[3])
        second_score = (
            float(engine_results[1][3])
            if len(engine_results) > 1
            else selected_score
        )
        confidence = self._confidence(best_score, second_score)

        mapped_formations = [
            self._map_formation_result(
                formation,
                lineup,
                ratings,
                score,
                best_score,
                is_best=(formation.name == best_name),
            )
            for formation, lineup, ratings, score in engine_results
        ]
        selected_formation = next(
            formation
            for formation in mapped_formations
            if formation.formation_name == selected_name
        )
        rankings = [
            self._ranking_row(
                formation,
                ratings,
                float(score),
                best_score,
                confidence,
                is_best=(formation.name == best_name),
                is_selected=(formation.name == selected_name),
            )
            for formation, _lineup, ratings, score in engine_results
        ]

        return IdealXIResult(
            mode=requested_name,
            selected_formation_name=selected_name,
            best_formation_name=best_name,
            overall_score=selected_score,
            confidence=confidence,
            reason=self._reason(
                selected_name,
                best_name,
                selected_score,
                best_score,
            ),
            rankings=rankings,
            formations=mapped_formations,
            selected_formation=selected_formation,
            team_profile=self._team_profile(
                selected[0],
                selected[2],
            ),
        )

    def _map_formation_result(
        self,
        formation,
        lineup,
        ratings,
        score,
        best_score,
        is_best=False,
    ):
        return FormationAnalysisResult(
            formation_name=formation.name,
            recommended_tactic="Roster fit",
            tactic_level=0.0,
            win_probability=0.0,
            draw_probability=0.0,
            loss_probability=0.0,
            possession=0.0,
            expected_goals=0.0,
            opponent_expected_goals=0.0,
            win_probability_delta=0.0,
            expected_goals_delta=float(score) - float(best_score),
            lineup=[
                self._map_lineup_player(index + 1, lineup_player)
                for index, lineup_player in enumerate(lineup.players)
            ],
            is_recommended=is_best,
            team_ratings=self._map_team_ratings(ratings),
        )

    def _map_lineup_player(self, number, lineup_player):
        return LineupPlayerResult(
            number=number,
            position=format_position(lineup_player.position),
            side=self._enum_value(lineup_player.side),
            order=self._enum_value(lineup_player.order),
            order_side=(
                self._enum_value(lineup_player.order_side)
                if lineup_player.order_side is not None
                else ""
            ),
            player_name=lineup_player.player.name,
        )

    def _ranking_row(
        self,
        formation,
        ratings,
        score,
        best_score,
        confidence,
        is_best=False,
        is_selected=False,
    ):
        mapped_ratings = self._map_team_ratings(ratings)
        return FormationRankingResult(
            formation_name=formation.name,
            overall_score=float(score),
            score_delta=float(score) - float(best_score),
            confidence=(
                confidence
                if is_best
                else t("squad_builder.confidence.alternative")
            ),
            reason=self._formation_reason(formation, mapped_ratings),
            midfield=mapped_ratings.midfield,
            attack=self._attack_score(mapped_ratings),
            defense=self._defense_score(mapped_ratings),
            experience=None,
            is_best=is_best,
            is_selected=is_selected,
        )

    def _team_profile(self, formation, ratings):
        mapped = self._map_team_ratings(ratings)
        sectors = [
            (t("squad_builder.sector.left_defense"), mapped.left_defense),
            (t("squad_builder.sector.central_defense"), mapped.central_defense),
            (t("squad_builder.sector.right_defense"), mapped.right_defense),
            (t("squad_builder.sector.midfield"), mapped.midfield),
            (t("squad_builder.sector.left_attack"), mapped.left_attack),
            (t("squad_builder.sector.central_attack"), mapped.central_attack),
            (t("squad_builder.sector.right_attack"), mapped.right_attack),
        ]
        ranked = sorted(
            sectors,
            key=lambda item: item[1],
            reverse=True,
        )
        return TeamProfileResult(
            strengths=tuple(label for label, _value in ranked[:2]),
            weaknesses=tuple(label for label, _value in ranked[-2:]),
            preferred_style=self._preferred_style(formation),
        )

    @staticmethod
    def _map_team_ratings(ratings):
        if ratings is None:
            return TeamRatingsResult()

        return TeamRatingsResult(
            left_defense=float(getattr(ratings, "left_defense", 0.0)),
            central_defense=float(getattr(ratings, "central_defense", 0.0)),
            right_defense=float(getattr(ratings, "right_defense", 0.0)),
            midfield=float(getattr(ratings, "midfield", 0.0)),
            left_attack=float(getattr(ratings, "left_attack", 0.0)),
            central_attack=float(getattr(ratings, "central_attack", 0.0)),
            right_attack=float(getattr(ratings, "right_attack", 0.0)),
        )

    @staticmethod
    def _attack_score(ratings):
        return (
            ratings.left_attack
            + ratings.central_attack
            + ratings.right_attack
        )

    @staticmethod
    def _defense_score(ratings):
        return (
            ratings.left_defense
            + ratings.central_defense
            + ratings.right_defense
        )

    @staticmethod
    def _confidence(best_score, second_score):
        gap = float(best_score) - float(second_score)

        if gap >= 12:
            return t("squad_builder.confidence.high")

        if gap >= 5:
            return t("squad_builder.confidence.medium")

        return t("squad_builder.confidence.close")

    @staticmethod
    def _preferred_style(formation):
        defenders = sum(
            amount
            for position, amount in formation.positions.items()
            if "DEFENDER" in position.value or "WING_BACK" in position.value
        )
        midfielders = sum(
            amount
            for position, amount in formation.positions.items()
            if "MIDFIELDER" in position.value or "WINGER" in position.value
        )
        forwards = sum(
            amount
            for position, amount in formation.positions.items()
            if "FORWARD" in position.value
        )

        if midfielders >= 5:
            return t("squad_builder.style.midfield_control")

        if forwards >= 3:
            return t("squad_builder.style.attacking")

        if defenders >= 5:
            return t("squad_builder.style.defensive_stability")

        return t("squad_builder.style.balanced")

    @staticmethod
    def _formation_reason(formation, ratings):
        overall = FormationAnalyzer.overall_score(ratings)
        return t(
            "squad_builder.reason.formation_fit",
            formation=formation.name,
            score=f"{overall:.2f}",
        )

    @staticmethod
    def _reason(selected_name, best_name, selected_score, best_score):
        if selected_name == best_name:
            return t(
                "squad_builder.reason.best",
                formation=selected_name,
            )

        delta = float(selected_score) - float(best_score)
        return t(
            "squad_builder.reason.manual",
            formation=selected_name,
            delta=f"{delta:.2f}",
        )

    @staticmethod
    def _enum_value(value):
        return getattr(value, "value", value)
