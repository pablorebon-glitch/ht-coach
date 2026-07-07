from dataclasses import dataclass, field

from models.lineup_player import LineupPlayer


@dataclass
class Team:
    players: list[LineupPlayer] = field(default_factory=list)

    def add_player(self, lineup_player: LineupPlayer):
        self.players.append(lineup_player)