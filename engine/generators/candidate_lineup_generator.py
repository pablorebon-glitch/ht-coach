from dataclasses import dataclass
from itertools import combinations

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.position_registry import POSITION_ENGINES

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.position import Position
from models.side import Side


@dataclass
class PartialLineup:

    players: list

    used_player_ids: frozenset

    score: float


class CandidateLineupGenerator:

    DEFAULT_CANDIDATES_PER_ROLE = 10

    DEFAULT_BEAM_WIDTH = 1000

    @staticmethod
    def _player_key(player):

        return id(player)

    @staticmethod
    def _build_roles(formation):

        roles = []

        for position, amount in formation.positions.items():

            if position.value not in POSITION_ENGINES:
                continue

            if (
                position in {
                    Position.WING_BACK,
                    Position.WINGER,
                }
                and amount == 2
            ):

                roles.append(
                    (
                        position,
                        Side.LEFT,
                        1
                    )
                )

                roles.append(
                    (
                        position,
                        Side.RIGHT,
                        1
                    )
                )

            elif (
                position in {
                    Position.WING_BACK,
                    Position.WINGER,
                }
                and amount == 1
            ):

                roles.append(
                    (
                        position,
                        Side.LEFT,
                        1
                    )
                )

            else:

                roles.append(
                    (
                        position,
                        Side.CENTER,
                        amount
                    )
                )

        return roles

    @classmethod
    def _build_rankings(
        cls,
        players,
        roles,
        candidates_per_role
    ):

        rankings = {}

        for position, side, _ in roles:

            role_key = (
                position,
                side
            )

            if role_key in rankings:
                continue

            rankings[role_key] = (
                PlayerAnalyzer.rank_players(
                    players,
                    position.value,
                    side
                )[:candidates_per_role]
            )

        return rankings

    @classmethod
    def generate(
        cls,
        players,
        formation,
        candidates_per_role=None,
        beam_width=None
    ):

        if candidates_per_role is None:

            candidates_per_role = (
                cls.DEFAULT_CANDIDATES_PER_ROLE
            )

        if beam_width is None:

            beam_width = (
                cls.DEFAULT_BEAM_WIDTH
            )

        roles = cls._build_roles(
            formation
        )

        rankings = cls._build_rankings(
            players,
            roles,
            candidates_per_role
        )

        beam = [
            PartialLineup(
                players=[],
                used_player_ids=frozenset(),
                score=0.0
            )
        ]

        for position, side, amount in roles:

            ranking = rankings[
                (
                    position,
                    side
                )
            ]

            player_combinations = list(
                combinations(
                    ranking,
                    amount
                )
            )

            next_beam = []

            for partial in beam:

                for player_scores in player_combinations:

                    selected_ids = frozenset(
                        cls._player_key(
                            player_score.player
                        )
                        for player_score
                        in player_scores
                    )

                    if (
                        partial.used_player_ids
                        & selected_ids
                    ):
                        continue

                    new_players = (
                        partial.players
                        + [
                            LineupPlayer(
                                player=player_score.player,
                                position=position,
                                side=side
                            )
                            for player_score
                            in player_scores
                        ]
                    )

                    new_score = (
                        partial.score
                        + sum(
                            player_score.score
                            for player_score
                            in player_scores
                        )
                    )

                    next_beam.append(
                        PartialLineup(
                            players=new_players,
                            used_player_ids=(
                                partial.used_player_ids
                                | selected_ids
                            ),
                            score=new_score
                        )
                    )

            next_beam.sort(
                key=lambda partial: partial.score,
                reverse=True
            )

            beam = next_beam[
                :beam_width
            ]

            if not beam:
                break

        expected_player_count = sum(
            amount
            for _, _, amount
            in roles
        )

        lineups = []

        seen_lineups = set()

        for partial in beam:

            if (
                len(partial.players)
                != expected_player_count
            ):
                continue

            lineup_key = tuple(
                sorted(
                    (
                        cls._player_key(
                            lineup_player.player
                        ),
                        lineup_player.position.value,
                        lineup_player.side.value
                    )
                    for lineup_player
                    in partial.players
                )
            )

            if lineup_key in seen_lineups:
                continue

            seen_lineups.add(
                lineup_key
            )

            lineups.append(
                Lineup(
                    players=partial.players
                )
            )

        return lineups