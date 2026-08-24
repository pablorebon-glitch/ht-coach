from dataclasses import dataclass

from models.team_ratings import TeamRatings


@dataclass
class Opponent:

    name: str

    ratings: TeamRatings

    created_at: str = ""
