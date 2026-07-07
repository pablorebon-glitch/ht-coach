from dataclasses import dataclass, field

from models.lineup_player import LineupPlayer


@dataclass
class Lineup:

    players: list[LineupPlayer] = field(default_factory=list)