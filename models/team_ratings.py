from dataclasses import dataclass


@dataclass
class TeamRatings:

    left_defense: float = 0

    central_defense: float = 0

    right_defense: float = 0

    midfield: float = 0

    left_attack: float = 0

    central_attack: float = 0

    right_attack: float = 0