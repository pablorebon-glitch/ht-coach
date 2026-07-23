from __future__ import annotations

from decimal import Decimal

from models.lineup import Lineup
from models.lineup_player import LineupPlayer

from engine.hattrick_ratings.models import HattrickRating, PredictionConfidence
from engine.hattrick_ratings.midfield.exceptions import InvalidMidfieldInput
from engine.hattrick_ratings.midfield.form_effects import form_modifier
from engine.hattrick_ratings.midfield.models import (
    MODEL_VERSION,
    MidfieldPrediction,
    MidfieldRatingInput,
    PlayerContributionBreakdown,
    PredictionBreakdown,
)
from engine.hattrick_ratings.midfield.order_effects import order_modifier
from engine.hattrick_ratings.midfield.stamina_effects import stamina_modifier
from engine.hattrick_ratings.midfield.team_context import context_modifiers


class MidfieldRatingCalculator:
    model_version = MODEL_VERSION

    def predict(self, rating_input: MidfieldRatingInput) -> MidfieldPrediction:
        lineup_players = _lineup_players(rating_input.lineup)
        self._validate_lineup(lineup_players)
        parameters = rating_input.context.model_parameters
        warnings: list[str] = ["model_uncalibrated"]
        contributions = []
        raw_score = Decimal("0.00")

        for item in lineup_players:
            player = item.player
            position = _enum_value(item.position)
            order = _enum_value(item.order)
            position_weight = parameters.position_weights.get(position, Decimal("0.00"))
            order_value, order_warning = order_modifier(
                item.position,
                item.order,
                parameters,
            )
            form_value, form_warning = form_modifier(
                getattr(player, "form", None),
                parameters,
            )
            stamina_value, stamina_warning = stamina_modifier(
                getattr(player, "stamina", None),
                rating_input.context.period,
                parameters,
            )
            player_warnings = tuple(
                warning
                for warning in (order_warning, form_warning, stamina_warning)
                if warning
            )
            warnings.extend(player_warnings)
            playmaking = Decimal(str(getattr(player, "playmaking", 0) or 0))
            contribution = (
                playmaking
                * position_weight
                * order_value
                * form_value
                * stamina_value
            )
            contribution = contribution.quantize(Decimal("0.0001"))
            raw_score += contribution
            contributions.append(
                PlayerContributionBreakdown(
                    player_name=getattr(player, "name", ""),
                    position=position,
                    order=order,
                    playmaking=playmaking,
                    position_weight=position_weight,
                    order_modifier=order_value,
                    form_modifier=form_value,
                    stamina_modifier=stamina_value,
                    contribution=contribution,
                    warning_codes=player_warnings,
                )
            )

        context_value, context_breakdown, context_warnings = context_modifiers(
            rating_input.context
        )
        warnings.extend(context_warnings)
        raw_rating = (
            parameters.base_rating
            + ((raw_score / parameters.playmaking_scale) * context_value)
        ).quantize(Decimal("0.0001"))
        rating = HattrickRating.from_decimal(raw_rating)
        unique_warnings = tuple(dict.fromkeys(warnings))
        confidence = _confidence(unique_warnings)
        return MidfieldPrediction(
            rating=rating,
            raw_rating=raw_rating,
            confidence=confidence,
            breakdown=PredictionBreakdown(
                player_contributions=tuple(contributions),
                context_modifiers=context_breakdown,
                raw_score=raw_score.quantize(Decimal("0.0001")),
                raw_rating=raw_rating,
                rounded_rating=rating,
                warning_codes=unique_warnings,
            ),
            model_version=self.model_version,
        )

    @staticmethod
    def _validate_lineup(lineup_players: list[LineupPlayer]) -> None:
        if not lineup_players:
            raise InvalidMidfieldInput("lineup is required")
        seen = set()
        for item in lineup_players:
            player = item.player
            identity = id(player)
            if identity in seen:
                raise InvalidMidfieldInput("duplicate player in lineup")
            seen.add(identity)
            injury = getattr(player, "injury", None)
            if injury is not None and float(injury) > 0:
                raise InvalidMidfieldInput("unavailable player in lineup")


def _lineup_players(lineup) -> list[LineupPlayer]:
    if isinstance(lineup, Lineup):
        return list(lineup.players)
    return list(lineup or [])


def _enum_value(value):
    return getattr(value, "value", str(value))


def _confidence(warnings: tuple[str, ...]) -> PredictionConfidence:
    if "model_uncalibrated" in warnings:
        return PredictionConfidence.UNCALIBRATED
    severe = {
        "unsupported_order",
        "missing_form_assumed",
        "missing_stamina_assumed",
    }
    if severe.intersection(warnings):
        return PredictionConfidence.LOW
    if warnings:
        return PredictionConfidence.MEDIUM
    return PredictionConfidence.HIGH
