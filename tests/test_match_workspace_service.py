import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
    MatchWorkspaceSettings,
)
from ht_coach_app.services.match_workspace_service import (
    MatchWorkspaceService,
    MatchWorkspaceValidationError,
)
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.opponent import Opponent
from models.order import Order
from models.position import Position
from models.side import Side
from models.tactic import Tactic
from models.team_ratings import TeamRatings


class FakeOpponentService:
    def __init__(self):
        self.opponent = Opponent(
            name="Rival FC",
            ratings=TeamRatings(
                left_defense=25,
                central_defense=35,
                right_defense=24,
                midfield=40,
                left_attack=25,
                central_attack=30,
                right_attack=24,
            )
        )

    def list_opponents(self):
        return [self.opponent]

    def get_opponent(self, name):
        if name == self.opponent.name:
            return self.opponent

        return None


def fake_importer(_path):
    return [
        SimpleNamespace(name="Keeper"),
        SimpleNamespace(name="Defender"),
    ]


def fake_optimizer(players, formations, _opponent_ratings):
    lineup = Lineup(
        players=[
            LineupPlayer(
                player=players[0],
                position=Position.GOALKEEPER,
                side=Side.CENTER,
                order=Order.NORMAL,
            ),
            LineupPlayer(
                player=players[1],
                position=Position.CENTRAL_DEFENDER,
                side=Side.CENTER,
                order=Order.DEFENSIVE,
                order_side=Side.LEFT,
            ),
        ]
    )

    return [
        SimpleNamespace(
            formation=formation,
            lineup=lineup,
            tactic=Tactic.PRESSING,
            tactic_level=7.25,
            probabilities=SimpleNamespace(
                win=0.5,
                draw=0.3,
                loss=0.2,
            ),
            match_evaluation=SimpleNamespace(
                possession=0.61,
                expected_goals=2.1,
                opponent_expected_goals=1.2,
            ),
        )
        for formation in formations
    ]


class MatchWorkspaceServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "players.csv"
        self.csv_path.write_text(
            "placeholder",
            encoding="utf-8"
        )
        self.service = MatchWorkspaceService(
            FakeOpponentService(),
            importer=fake_importer,
            optimizer=fake_optimizer
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_requires_existing_players_csv(self):
        with self.assertRaises(MatchWorkspaceValidationError):
            self.service.validate_inputs(
                "",
                "Rival FC",
                ["3-5-2"]
            )

        with self.assertRaises(MatchWorkspaceValidationError):
            self.service.validate_inputs(
                Path(self.temp_dir.name) / "missing.csv",
                "Rival FC",
                ["3-5-2"]
            )

    def test_requires_opponent_and_formation(self):
        with self.assertRaises(MatchWorkspaceValidationError):
            self.service.validate_inputs(
                self.csv_path,
                "",
                ["3-5-2"]
            )

        with self.assertRaises(MatchWorkspaceValidationError):
            self.service.validate_inputs(
                self.csv_path,
                "Rival FC",
                []
            )

    def test_rejects_unsupported_formation(self):
        with self.assertRaises(MatchWorkspaceValidationError):
            self.service.validate_inputs(
                self.csv_path,
                "Rival FC",
                ["1-1-8"]
            )

    def test_supported_formations_are_full_catalog(self):
        self.assertEqual(
            self.service.supported_formations(),
            [
                "2-5-3",
                "3-4-3",
                "3-5-2",
                "4-3-3",
                "4-4-2",
                "4-5-1",
                "5-2-3",
                "5-3-2",
                "5-4-1",
            ]
        )

    def test_default_formations_preserve_existing_user_selection(self):
        self.assertEqual(
            self.service.default_formations(),
            ["3-5-2", "4-5-1"]
        )

    def test_maps_engine_result_for_match_page(self):
        result = self.service.analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2"]
        )

        formation = result.formations[0]

        self.assertEqual(result.player_count, 2)
        self.assertEqual(formation.formation_name, "3-5-2")
        self.assertEqual(formation.recommended_tactic, "Pressing")
        self.assertEqual(formation.tactic_level, 7.25)
        self.assertEqual(formation.win_probability, 0.5)
        self.assertEqual(formation.possession, 0.61)
        self.assertTrue(formation.is_recommended)
        self.assertEqual(
            formation.lineup[0].position,
            "Goalkeeper (GK)"
        )
        self.assertEqual(
            formation.lineup[1].order_side,
            "LEFT"
        )
        self.assertEqual(
            formation.lineup[0].position,
            "Goalkeeper (GK)"
        )


class MatchWorkspaceRepositoryTest(unittest.TestCase):
    def test_settings_round_trip_to_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "settings.json"
            repository = MatchWorkspaceRepository(
                storage_path
            )

            repository.save(
                MatchWorkspaceSettings(
                    players_csv_path="C:/data/players.csv",
                    opponent_name="Rival FC",
                    selected_formations=["3-5-2", "4-5-1"]
                )
            )

            settings = repository.load()

            self.assertEqual(
                settings.players_csv_path,
                "C:/data/players.csv"
            )
            self.assertEqual(
                settings.opponent_name,
                "Rival FC"
            )
            self.assertEqual(
                settings.selected_formations,
                ["3-5-2", "4-5-1"]
            )

    def test_settings_default_to_favorites_for_existing_users(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MatchWorkspaceRepository(
                Path(temp_dir) / "missing.json"
            )

            settings = repository.load()

            self.assertEqual(
                settings.selected_formations,
                ["3-5-2", "4-5-1"]
            )


if __name__ == "__main__":
    unittest.main()
