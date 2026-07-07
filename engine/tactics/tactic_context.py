from dataclasses import dataclass

from models.tactic import Tactic


@dataclass(frozen=True)
class TacticContext:

    tactic: Tactic

    level: float

    lineup: object | None

    base_ratings: object

    opponent_ratings: object