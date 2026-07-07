from dataclasses import dataclass

from models.player import Player


@dataclass
class PlayerScore:

    player: Player
    score: float