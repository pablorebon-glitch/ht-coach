from engine.analyzers.player_analyzer import PlayerAnalyzer
from ht_coach_app.core.order_formatting import format_order
from ht_coach_app.core.position_formatting import (
    format_position,
    normalize_position_key,
)
from ht_coach_app.core.side_formatting import format_side
from ht_coach_app.player_intelligence.alternative_analyzer import (
    AlternativeAnalyzer,
)
from ht_coach_app.player_intelligence.contribution_formatter import (
    ContributionFormatter,
)
from ht_coach_app.player_intelligence.explanation_rules import (
    PlayerExplanationRules,
)
from ht_coach_app.player_intelligence.models import (
    PlayerIntelligenceViewModel,
    unavailable_player_intelligence,
)
from ht_coach_app.player_intelligence.profile_classifier import (
    PlayerProfileClassifier,
)
from models.side import Side


class PlayerIntelligenceService:
    def __init__(
        self,
        analyzer=PlayerAnalyzer,
        profile_classifier=None,
        explanation_rules=None,
        alternative_analyzer=None,
        contribution_formatter=None,
    ):
        self._analyzer = analyzer
        self._profile_classifier = profile_classifier or PlayerProfileClassifier()
        self._explanation_rules = explanation_rules or PlayerExplanationRules()
        self._alternative_analyzer = alternative_analyzer or AlternativeAnalyzer(
            analyzer
        )
        self._contribution_formatter = contribution_formatter or ContributionFormatter()

    def analyze(self, player_card, roster_players):
        if player_card is None:
            return unavailable_player_intelligence(
                "Select a player on the pitch to inspect details."
            )

        if not roster_players:
            return unavailable_player_intelligence(
                "Detailed roster information is unavailable for this restored result."
            )

        player = self._find_player(
            roster_players,
            player_card.player_name,
        )

        if player is None:
            return unavailable_player_intelligence(
                "This player is not available in the loaded roster data."
            )

        position = normalize_position_key(player_card.position)
        side = self._side(player_card.side)
        rank, score = self._alternative_analyzer.selected_rank(
            player,
            roster_players,
            position,
            side,
        )
        alternatives = self._alternative_analyzer.rank(
            player,
            roster_players,
            position,
            side,
        )
        best_position, best_score = self._analyzer.best_position(player)
        best_position_key = normalize_position_key(best_position)
        profile_label, profile_summary = self._profile_classifier.classify(
            player,
            position,
        )
        contributions = self._contribution_formatter.build(
            player,
            position,
            side,
            roster_players,
        )
        strengths = self._explanation_rules.strengths(
            player,
            position,
            roster_players,
        )
        limitations = self._explanation_rules.limitations(
            player,
            position,
            best_position_key,
        )
        why_selected = self._explanation_rules.why_selected(
            rank,
            score,
            alternatives,
        )

        return PlayerIntelligenceViewModel(
            player_id=player_card.player_id,
            player_name=player_card.player_name,
            headline=self._headline(
                player_card.player_name,
                profile_label,
                position,
                rank,
                alternatives,
            ),
            profile_label=profile_label,
            profile_summary=profile_summary,
            current_position=position,
            current_position_label=format_position(position),
            current_order=player_card.individual_order,
            current_order_label=format_order(player_card.individual_order),
            best_position=best_position_key,
            best_position_label=format_position(best_position_key),
            overall_score=float(score),
            overall_score_label=f"{score:.2f}",
            strengths=strengths,
            limitations=limitations,
            why_selected=why_selected,
            tactical_contributions=contributions,
            alternatives=alternatives,
            technical_attributes=self._technical_attributes(
                player,
                player_card,
                score,
                best_score,
            ),
        )

    def _headline(self, name, profile, position, rank, alternatives):
        role = format_position(position)
        if rank == 1:
            first = f"{name} is the strongest evaluated option available for this {role} role."
        elif rank is None:
            first = f"{name} was selected by the optimizer for this analyzed lineup."
        else:
            first = f"{name} is a {profile.lower()} selected for this {role} role."

        if alternatives:
            alt = alternatives[0]
            second = (
                "The closest alternative has a lower player score."
                if alt.score_difference < -0.25
                else "The closest alternative is very close on player score."
            )
        else:
            second = "No same-role alternative is available in the loaded roster."

        return f"{first} {second}"

    @staticmethod
    def _find_player(players, player_name):
        for player in players:
            if player.name == player_name:
                return player

        return None

    @staticmethod
    def _side(side):
        value = getattr(side, "value", side)
        try:
            return Side(str(value))
        except ValueError:
            return Side.CENTER

    @staticmethod
    def _technical_attributes(player, player_card, score, best_score):
        attributes = [
            ("Age", str(getattr(player, "age", ""))),
            ("Form", str(getattr(player, "form", ""))),
            ("Stamina", str(getattr(player, "stamina", ""))),
            ("Experience", str(getattr(player, "experience", ""))),
            ("Leadership", str(getattr(player, "leadership", ""))),
            ("TSI", str(getattr(player, "tsi", ""))),
            ("Salary", str(getattr(player, "salary", ""))),
            ("Current position", player_card.position_label),
            ("Order", player_card.order_label),
            ("Side", player_card.side_label),
            ("Player score difference", "not a win-probability difference"),
            ("Positional score", f"{score:.2f}"),
            ("Best-position score", f"{float(best_score):.2f}"),
            ("Goalkeeper", str(getattr(player, "goalkeeper", ""))),
            ("Defending", str(getattr(player, "defending", ""))),
            ("Playmaking", str(getattr(player, "playmaking", ""))),
            ("Winger", str(getattr(player, "winger", ""))),
            ("Passing", str(getattr(player, "passing", ""))),
            ("Scoring", str(getattr(player, "scoring", ""))),
            ("Set pieces", str(getattr(player, "set_pieces", ""))),
            ("Specialty", str(getattr(player, "speciality", ""))),
        ]

        return tuple(
            (label, value)
            for label, value in attributes
            if value != ""
        )
