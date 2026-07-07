from dataclasses import dataclass

from models.player import Player
from models.position import Position


@dataclass
class PlayerAnalysis:

    player: Player

    best_position: Position

    score: float