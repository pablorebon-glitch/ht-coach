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
from models.tactic import Tactic


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
class PlayerContributionResult:
    player_name: str
    value_label: str = ""


@dataclass(frozen=True)
class FormationAffinityResult:
    formation_name: str
    level: str
    overall_score: float
    score_delta: float
    is_best: bool = False


@dataclass(frozen=True)
class TacticalReadinessResult:
    tactic_name: str
    level: str
    why_suitable: str
    strengths: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    contributors: tuple[PlayerContributionResult, ...] = ()
    compatible_formations: tuple[str, ...] = ()


@dataclass(frozen=True)
class SquadIdentityResult:
    identity: str = ""
    explanation: str = ""
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    contributors: tuple[PlayerContributionResult, ...] = ()
    tactical_readiness: list[TacticalReadinessResult] = field(default_factory=list)
    formation_affinity: list[FormationAffinityResult] = field(default_factory=list)


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
    squad_identity: SquadIdentityResult = field(default_factory=SquadIdentityResult)


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
                squad_identity=SquadIdentityResult(
                    identity=t("squad_identity.empty_title"),
                    explanation=t("squad_identity.empty_message"),
                ),
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
        identity = self._squad_identity(
            players,
            selected[0],
            selected[2],
            rankings,
        )

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
            squad_identity=identity,
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

    def _squad_identity(self, players, formation, ratings, rankings):
        mapped = self._map_team_ratings(ratings)
        strengths, weaknesses = self._strengths_and_weaknesses(mapped)
        identity_key = self._identity_key(formation, mapped)
        contributors = self._contributors_for_identity(
            players,
            identity_key,
        )
        affinity = [
            FormationAffinityResult(
                formation_name=ranking.formation_name,
                level=self._affinity_level(
                    ranking.overall_score,
                    rankings[0].overall_score if rankings else 0.0,
                ),
                overall_score=ranking.overall_score,
                score_delta=ranking.score_delta,
                is_best=ranking.is_best,
            )
            for ranking in rankings
        ]

        return SquadIdentityResult(
            identity=t(f"squad_identity.identity.{identity_key}"),
            explanation=t(f"squad_identity.explanation.{identity_key}"),
            strengths=strengths,
            weaknesses=weaknesses,
            contributors=contributors,
            tactical_readiness=self._tactical_readiness(
                players,
                formation,
                mapped,
                affinity,
            ),
            formation_affinity=affinity,
        )

    def _strengths_and_weaknesses(self, ratings):
        sectors = [
            (t("squad_builder.sector.left_defense"), ratings.left_defense),
            (t("squad_builder.sector.central_defense"), ratings.central_defense),
            (t("squad_builder.sector.right_defense"), ratings.right_defense),
            (t("squad_builder.sector.midfield"), ratings.midfield),
            (t("squad_builder.sector.left_attack"), ratings.left_attack),
            (t("squad_builder.sector.central_attack"), ratings.central_attack),
            (t("squad_builder.sector.right_attack"), ratings.right_attack),
        ]
        ranked = sorted(
            sectors,
            key=lambda item: item[1],
            reverse=True,
        )
        return (
            tuple(label for label, _value in ranked[:2]),
            tuple(label for label, _value in ranked[-2:]),
        )

    def _identity_key(self, formation, ratings):
        wing_attack = (
            ratings.left_attack
            + ratings.right_attack
        ) / 2
        defense = self._defense_score(ratings) / 3

        if ratings.midfield >= max(wing_attack, ratings.central_attack, defense):
            return "midfield_dominant"

        if wing_attack > ratings.central_attack + 2:
            return "wing_oriented"

        if ratings.central_attack >= max(wing_attack, defense):
            return "central_attack"

        if defense > max(ratings.midfield, ratings.central_attack, wing_attack):
            return "defensive"

        if self._formation_count(formation, "DEFENDER") >= 5:
            return "counter_oriented"

        return "balanced"

    def _tactical_readiness(self, players, formation, ratings, affinity):
        raw_scores = [
            (
                tactic.value,
                self._readiness_score(tactic, players, formation, ratings),
            )
            for tactic in [
                Tactic.NORMAL,
                Tactic.ATTACK_IN_MIDDLE,
                Tactic.ATTACK_ON_WINGS,
                Tactic.PLAY_CREATIVELY,
                Tactic.PRESSING,
                Tactic.COUNTER_ATTACKS,
                Tactic.LONG_SHOTS,
            ]
        ]
        best_score = max(
            (score for _name, score in raw_scores),
            default=1.0,
        )
        compatible_formations = tuple(
            item.formation_name
            for item in affinity[:3]
        )

        return [
            TacticalReadinessResult(
                tactic_name=name,
                level=self._readiness_level(score, best_score),
                why_suitable=t(
                    "squad_identity.readiness.why",
                    tactic=name,
                    level=self._readiness_level(score, best_score),
                ),
                strengths=self._readiness_strengths(name),
                limitations=self._readiness_limitations(name, score, best_score),
                contributors=self._contributors_for_tactic(
                    players,
                    name,
                ),
                compatible_formations=compatible_formations,
            )
            for name, score in sorted(
                raw_scores,
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    def _readiness_score(self, tactic, players, formation, ratings):
        averages = self._player_averages(players)
        defense = self._defense_score(ratings) / 3
        attack = self._attack_score(ratings) / 3
        wing_attack = (
            ratings.left_attack
            + ratings.right_attack
        ) / 2
        formation_bonus = self._formation_bonus(tactic, formation)

        if tactic == Tactic.NORMAL:
            return (
                self._overall_rating(ratings)
                + averages["form"]
                + averages["stamina"]
                + formation_bonus
            )

        if tactic == Tactic.ATTACK_IN_MIDDLE:
            return (
                ratings.midfield
                + ratings.central_attack
                + averages["passing"]
                + formation_bonus
            )

        if tactic == Tactic.ATTACK_ON_WINGS:
            return (
                wing_attack
                + averages["winger"]
                + averages["passing"]
                + formation_bonus
            )

        if tactic == Tactic.PLAY_CREATIVELY:
            return (
                averages["passing"]
                + averages["experience"]
                + averages["speciality"]
                + formation_bonus
            )

        if tactic == Tactic.PRESSING:
            return (
                defense
                + averages["stamina"]
                + averages["form"]
                + formation_bonus
            )

        if tactic == Tactic.COUNTER_ATTACKS:
            return (
                defense
                + averages["passing"]
                + averages["experience"]
                + formation_bonus
            )

        if tactic == Tactic.LONG_SHOTS:
            return (
                ratings.midfield
                + averages["scoring"]
                + averages["set_pieces"]
                + formation_bonus
            )

        return 0.0

    @staticmethod
    def _readiness_level(score, best_score):
        ratio = 0.0 if best_score <= 0 else float(score) / float(best_score)

        if ratio >= 0.9:
            return t("squad_identity.level.excellent")

        if ratio >= 0.75:
            return t("squad_identity.level.high")

        if ratio >= 0.55:
            return t("squad_identity.level.medium")

        if ratio >= 0.35:
            return t("squad_identity.level.low")

        return t("squad_identity.level.very_low")

    @staticmethod
    def _affinity_level(score, best_score):
        ratio = 0.0 if best_score <= 0 else float(score) / float(best_score)

        if ratio >= 0.95:
            return t("squad_identity.level.excellent")

        if ratio >= 0.85:
            return t("squad_identity.level.high")

        if ratio >= 0.7:
            return t("squad_identity.level.medium")

        if ratio >= 0.55:
            return t("squad_identity.level.low")

        return t("squad_identity.level.very_low")

    @staticmethod
    def _readiness_strengths(tactic_name):
        return (
            t("squad_identity.readiness.strength", tactic=tactic_name),
        )

    @staticmethod
    def _readiness_limitations(tactic_name, score, best_score):
        if best_score <= 0 or score / best_score >= 0.75:
            return (
                t("squad_identity.readiness.limitation_context", tactic=tactic_name),
            )

        return (
            t("squad_identity.readiness.limitation_gap", tactic=tactic_name),
        )

    def _contributors_for_identity(self, players, identity_key):
        if identity_key == "wing_oriented":
            fields = ("winger", "passing")
        elif identity_key == "central_attack":
            fields = ("scoring", "passing", "playmaking")
        elif identity_key == "defensive":
            fields = ("defending", "stamina")
        elif identity_key == "counter_oriented":
            fields = ("defending", "passing", "experience")
        elif identity_key == "midfield_dominant":
            fields = ("playmaking", "passing", "stamina")
        else:
            fields = ("form", "stamina", "experience")

        return self._top_contributors(players, fields)

    def _contributors_for_tactic(self, players, tactic_name):
        field_map = {
            Tactic.NORMAL.value: ("form", "stamina", "experience"),
            Tactic.ATTACK_IN_MIDDLE.value: ("playmaking", "passing", "scoring"),
            Tactic.ATTACK_ON_WINGS.value: ("winger", "passing", "scoring"),
            Tactic.PLAY_CREATIVELY.value: ("passing", "experience", "speciality"),
            Tactic.PRESSING.value: ("defending", "stamina", "form"),
            Tactic.COUNTER_ATTACKS.value: ("defending", "passing", "experience"),
            Tactic.LONG_SHOTS.value: ("scoring", "set_pieces", "playmaking"),
        }
        return self._top_contributors(
            players,
            field_map.get(tactic_name, ("form", "stamina")),
        )

    def _top_contributors(self, players, fields, limit=3):
        scored = []

        for player in players:
            score = sum(
                self._player_field_value(player, field)
                for field in fields
            )
            scored.append((player, score))

        scored.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return tuple(
            PlayerContributionResult(
                player_name=player.name,
                value_label=f"{score:.0f}",
            )
            for player, score in scored[:limit]
        )

    def _player_averages(self, players):
        fields = [
            "form",
            "stamina",
            "passing",
            "experience",
            "scoring",
            "set_pieces",
            "winger",
        ]

        if not players:
            return {
                field: 0.0
                for field in fields + ["speciality"]
            }

        averages = {
            field: sum(
                float(getattr(player, field, 0.0) or 0.0)
                for player in players
            ) / len(players)
            for field in fields
        }
        averages["speciality"] = sum(
            1.0
            for player in players
            if str(getattr(player, "speciality", "") or "").strip()
        ) / len(players) * 10.0
        return averages

    @staticmethod
    def _player_field_value(player, field):
        if field == "speciality":
            return 10.0 if str(getattr(player, "speciality", "") or "").strip() else 0.0

        return float(getattr(player, field, 0.0) or 0.0)

    def _formation_bonus(self, tactic, formation):
        if tactic == Tactic.ATTACK_IN_MIDDLE:
            return self._formation_count(formation, "INNER_MIDFIELDER")

        if tactic == Tactic.ATTACK_ON_WINGS:
            return self._formation_count(formation, "WINGER")

        if tactic == Tactic.PRESSING:
            return self._formation_count(formation, "DEFENDER")

        if tactic == Tactic.COUNTER_ATTACKS:
            return self._formation_count(formation, "DEFENDER") + 1

        if tactic == Tactic.LONG_SHOTS:
            return self._formation_count(formation, "INNER_MIDFIELDER")

        return 1.0

    @staticmethod
    def _formation_count(formation, token):
        return sum(
            amount
            for position, amount in formation.positions.items()
            if token in position.value
        )

    @staticmethod
    def _overall_rating(ratings):
        return FormationAnalyzer.overall_score(ratings) / 7

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
