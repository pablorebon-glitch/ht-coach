from __future__ import annotations

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.player import Player
from models.position import Position
from models.side import Side

from engine.hattrick_ratings.midfield.calculator import MidfieldRatingCalculator
from engine.hattrick_ratings.midfield.models import (
    MatchPeriod,
    MidfieldRatingContext,
    MidfieldRatingInput,
    TeamAttitude,
)
from engine.rating_validation.fixture import (
    PredictedRatings,
    RatingPredictionProvider,
    RatingValidationFixture,
)


class MidfieldRatingPredictionProvider(RatingPredictionProvider):
    provider_name = "hattrick-midfield-v1"

    def __init__(self, calculator=None):
        self._calculator = calculator or MidfieldRatingCalculator()

    def predict_fixture(self, fixture: RatingValidationFixture) -> PredictedRatings:
        lineup = lineup_from_fixture(fixture)
        prediction = self._calculator.predict(
            MidfieldRatingInput(
                lineup=lineup,
                formation=fixture.formation,
                context=context_from_fixture(fixture),
            )
        )
        return PredictedRatings(
            midfield=float(prediction.rating.decimal),
            provider=prediction.model_version,
        )

    def predict_lineup(self, lineup, context=None) -> PredictedRatings:
        prediction = self._calculator.predict(
            MidfieldRatingInput(
                lineup=lineup,
                context=context or MidfieldRatingContext(),
            )
        )
        return PredictedRatings(
            midfield=float(prediction.rating.decimal),
            provider=prediction.model_version,
        )


def lineup_from_fixture(fixture: RatingValidationFixture) -> Lineup:
    players = fixture.additional_context.get("lineup_players", ())
    lineup_players = []
    for entry in players:
        lineup_players.append(
            LineupPlayer(
                player=Player(
                    name=entry.get("name", ""),
                    age=int(entry.get("age", 20)),
                    days=int(entry.get("days", 0)),
                    speciality=entry.get("speciality", ""),
                    form=int(entry.get("form", 7)),
                    stamina=int(entry.get("stamina", 7)),
                    goalkeeper=int(entry.get("goalkeeper", 0)),
                    defending=int(entry.get("defending", 0)),
                    playmaking=int(entry.get("playmaking", 0)),
                    winger=int(entry.get("winger", 0)),
                    passing=int(entry.get("passing", 0)),
                    scoring=int(entry.get("scoring", 0)),
                    set_pieces=int(entry.get("set_pieces", 0)),
                    experience=int(entry.get("experience", 0)),
                    leadership=int(entry.get("leadership", 0)),
                    tsi=int(entry.get("tsi", 0)),
                    salary=int(entry.get("salary", 0)),
                ),
                position=Position(entry.get("position", "INNER_MIDFIELDER")),
                side=Side(entry.get("side", "CENTER")),
                order=Order(entry.get("order", "Normal")),
                order_side=(
                    Side(entry["order_side"])
                    if entry.get("order_side")
                    else None
                ),
            )
        )
    return Lineup(lineup_players)


def context_from_fixture(fixture: RatingValidationFixture) -> MidfieldRatingContext:
    context = fixture.additional_context.get("midfield_context", {})
    attitude = context.get("attitude") or fixture.attitude or TeamAttitude.NORMAL.value
    return MidfieldRatingContext(
        team_spirit=context.get("team_spirit"),
        attitude=attitude,
        period=context.get("period", MatchPeriod.START.value),
        coach=fixture.coach,
    )
