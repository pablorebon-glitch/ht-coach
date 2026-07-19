import tempfile
import unittest
from pathlib import Path

from engine.optimizers.lineup_optimizer import LineupOptimizer
from engine.squad_health.availability_classifier import AvailabilityClassifier
from engine.squad_health.availability_service import (
    CURRENT_AVAILABLE,
    FULL_STRENGTH,
)
from engine.squad_health.models import AvailabilityStatus
from importers.csv_importer import parse_injury_value
from ht_coach_app.services.squad_builder_service import SquadBuilderService
from ht_coach_app.services.squad_service import SquadService
from models.formations import FORMATION_BY_NAME
from models.player import Player


class RatingStub:
    def __init__(self, value):
        self.left_defense = value
        self.central_defense = value + 1
        self.right_defense = value
        self.midfield = value + 2
        self.left_attack = value
        self.central_attack = value + 3
        self.right_attack = value


def make_player(name, skill=5, injury=None):
    return Player(
        name=name,
        age=22,
        days=0,
        speciality="Quick" if skill >= 10 else "",
        form=skill,
        stamina=skill,
        goalkeeper=skill,
        defending=skill,
        playmaking=skill,
        winger=skill,
        passing=skill,
        scoring=skill,
        set_pieces=skill,
        experience=skill,
        leadership=skill,
        tsi=skill * 1000,
        salary=skill * 100,
        injury=injury,
        injury_raw="" if injury is None else str(injury),
    )


class SquadHealthTest(unittest.TestCase):
    def test_csv_injury_parser_handles_expected_values(self):
        self.assertEqual(parse_injury_value(""), (None, ""))
        self.assertEqual(parse_injury_value("0"), (0.0, "0"))
        self.assertEqual(parse_injury_value("3"), (3.0, "3"))
        self.assertEqual(parse_injury_value("2.5"), (2.5, "2.5"))
        self.assertEqual(parse_injury_value("bad"), (None, "bad"))

    def test_availability_classifier_states(self):
        available = AvailabilityClassifier.classify(
            make_player("Available", injury=0)
        )
        injured = AvailabilityClassifier.classify(
            make_player("Injured", injury=3)
        )
        unknown = AvailabilityClassifier.classify(
            make_player("Unknown", injury=None)
        )
        unknown_player = make_player("Malformed", injury=None)
        unknown_player.injury_raw = "bad"
        malformed = AvailabilityClassifier.classify(unknown_player)

        self.assertEqual(available.status, AvailabilityStatus.AVAILABLE)
        self.assertTrue(available.eligible_for_selection)
        self.assertEqual(injured.status, AvailabilityStatus.INJURED)
        self.assertFalse(injured.eligible_for_selection)
        self.assertEqual(unknown.status, AvailabilityStatus.AVAILABLE)
        self.assertEqual(malformed.status, AvailabilityStatus.UNKNOWN)

    def test_injured_player_excluded_from_current_available_optimization(self):
        players = [make_player("Injured Star", 20, injury=3)] + [
            make_player(f"Player {index}", 8, injury=0)
            for index in range(1, 23)
        ]
        seen = []

        def optimizer(candidates, formations):
            seen.append([player.name for player in candidates])
            return [
                (
                    formation,
                    LineupOptimizer.optimize(candidates, formation),
                    RatingStub(10 - index),
                    100 - index,
                )
                for index, formation in enumerate(formations)
            ]

        service = SquadBuilderService(optimizer=optimizer)
        result = service.build(
            players,
            availability_mode=CURRENT_AVAILABLE,
        )

        self.assertNotIn("Injured Star", seen[0])
        self.assertFalse(
            any(
                player.player_name == "Injured Star"
                for player in result.selected_formation.lineup
            )
        )
        self.assertEqual(result.health_summary.available_count, 22)
        self.assertEqual(
            result.health_summary.unavailable_players[0].player_name,
            "Injured Star",
        )

    def test_injured_player_included_in_full_strength_simulation(self):
        players = [make_player("Injured Star", 20, injury=3)] + [
            make_player(f"Player {index}", 8, injury=0)
            for index in range(1, 23)
        ]
        seen = []

        def optimizer(candidates, formations):
            seen.append([player.name for player in candidates])
            return [
                (
                    formation,
                    LineupOptimizer.optimize(candidates, formation),
                    RatingStub(10 - index),
                    100 - index,
                )
                for index, formation in enumerate(formations)
            ]

        service = SquadBuilderService(optimizer=optimizer)
        result = service.build(
            players,
            availability_mode=FULL_STRENGTH,
        )

        self.assertIn("Injured Star", seen[0])
        self.assertTrue(result.simulation_warning)

    def test_players_table_availability_filter(self):
        players = [
            make_player("Ready", 8, injury=0),
            make_player("Hurt", 8, injury=2),
        ]
        service = SquadService(importer=lambda _path: players)
        rows = service.map_players(players)

        injured = service.filter_rows(
            rows,
            availability="injured",
        )

        self.assertEqual([row.name for row in injured], ["Hurt"])
        self.assertEqual(injured[0].availability_filter_key, "injured")


if __name__ == "__main__":
    unittest.main()
