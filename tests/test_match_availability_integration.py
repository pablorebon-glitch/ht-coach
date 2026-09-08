import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from engine.squad_health.availability_service import (
    CURRENT_AVAILABLE,
    FULL_STRENGTH,
)
from engine.weekly_training.models import TrainingSlotClass
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_rules import PlaymakingTrainingRules
from ht_coach_app.services.match_workspace_service import (
    MATCH_TYPE_CUP,
    MatchWorkspaceService,
    MatchWorkspaceValidationError,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)
from ht_coach_app.widgets.formation_board.formation_board_models import (
    FormationBoardViewModel,
    FormationSlotViewModel,
    PlayerCardViewModel,
)
from ht_coach_app.workspace.workspace_models import WorkspaceState
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.opponent import Opponent
from models.order import Order
from models.player import Player
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
            ),
        )

    def list_opponents(self):
        return [self.opponent]

    def get_opponent(self, name):
        if name == self.opponent.name:
            return self.opponent

        return None


def make_player(name, skill=8, injury=0):
    return Player(
        name=name,
        age=22,
        days=0,
        speciality="",
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


def make_players():
    return [make_player("Injured Star", skill=20, injury=3)] + [
        make_player(f"Player {index}", skill=8, injury=0)
        for index in range(1, 13)
    ]


def optimizer_spy(seen):
    def optimize(players, formations, _opponent_ratings):
        seen.append([player.name for player in players])
        lineup = Lineup(
            players=[
                LineupPlayer(
                    player=player,
                    position=Position.GOALKEEPER if index == 0 else Position.FORWARD,
                    side=Side.CENTER,
                    order=Order.NORMAL,
                )
                for index, player in enumerate(players[:11])
            ]
        )
        return [
            SimpleNamespace(
                formation=formation,
                lineup=lineup,
                tactic=Tactic.NORMAL,
                tactic_level=6.0,
                ratings=TeamRatings(),
                probabilities=SimpleNamespace(win=0.5, draw=0.3, loss=0.2),
                match_evaluation=SimpleNamespace(
                    possession=0.55,
                    expected_goals=2.0,
                    opponent_expected_goals=1.1,
                ),
            )
            for formation in formations
        ]

    return optimize


def board_with_players(player_names):
    slots = []
    for index, name in enumerate(player_names):
        player = PlayerCardViewModel(
            player_id=name,
            player_name=name,
            display_name=name,
            position="GOALKEEPER" if index == 0 else "FORWARD",
            position_label="Goalkeeper (GK)" if index == 0 else "Forward (F)",
            position_abbreviation="GK" if index == 0 else "F",
            side="CENTER",
            side_label="Center",
            individual_order="NORMAL",
            order_label="Normal",
        )
        slots.append(
            FormationSlotViewModel(
                slot_id=f"slot-{index}",
                line="test",
                side="CENTER",
                side_label="Center",
                position=player.position,
                position_label=player.position_label,
                normalized_x=0.5,
                normalized_y=0.1 * index,
                player=player,
            )
        )

    return FormationBoardViewModel(
        formation_name="3-5-2",
        tactic_name="Normal",
        tactic_level=0,
        slots=tuple(slots),
    )


class MatchAvailabilityIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "players.csv"
        self.csv_path.write_text("placeholder", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def service(self, players, seen=None):
        return MatchWorkspaceService(
            FakeOpponentService(),
            importer=lambda _path: players,
            optimizer=optimizer_spy(seen if seen is not None else []),
        )

    def test_current_available_excludes_injured_players_from_match_optimizer(self):
        players = make_players()
        seen = []
        result = self.service(players, seen).analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2"],
            availability_mode=CURRENT_AVAILABLE,
        )

        self.assertNotIn("Injured Star", seen[0])
        self.assertEqual(result.player_count, 12)
        self.assertEqual(result.unavailable_players_count, 1)
        self.assertEqual(result.availability_warning, "")

    def test_full_strength_includes_injured_players_with_warning(self):
        players = make_players()
        seen = []
        result = self.service(players, seen).analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2"],
            availability_mode=FULL_STRENGTH,
        )

        self.assertIn("Injured Star", seen[0])
        self.assertEqual(result.player_count, 13)
        self.assertEqual(result.availability_mode, FULL_STRENGTH)
        self.assertTrue(result.availability_warning)

    def test_roster_loading_respects_availability_mode(self):
        players = make_players()
        service = self.service(players)

        current_names = [
            player.name
            for player in service.load_players(self.csv_path)
        ]
        full_strength_names = [
            player.name
            for player in service.load_players(
                self.csv_path,
                availability_mode=FULL_STRENGTH,
            )
        ]

        self.assertNotIn("Injured Star", current_names)
        self.assertIn("Injured Star", full_strength_names)

    def test_workspace_recalculation_rejects_injured_selected_player_by_default(self):
        players = make_players()
        names = ["Injured Star"] + [f"Player {index}" for index in range(1, 11)]
        workspace_state = WorkspaceState(
            workspace_boards={"3-5-2": board_with_players(names)},
            current_formation_name="3-5-2",
        )

        with self.assertRaisesRegex(
            MatchWorkspaceValidationError,
            "Injured Star is not available",
        ):
            self.service(players).analyze_workspace(
                self.csv_path,
                "Rival FC",
                workspace_state,
            )

    def test_result_serialization_preserves_availability_metadata(self):
        result = self.service(make_players()).analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2"],
            availability_mode=FULL_STRENGTH,
        )

        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(result)
        )

        self.assertEqual(restored.availability_mode, FULL_STRENGTH)
        self.assertEqual(restored.unavailable_players_count, 1)
        self.assertEqual(
            restored.availability_warning,
            result.availability_warning,
        )

    def test_required_50_available_player_beats_injured_competitor_for_half_training_slot(self):
        required_half = make_player("Required Half", skill=5, injury=0)
        injured_competitor = make_player("Injured Half Star", skill=20, injury=3)
        players = [
            make_player("Goalkeeper", skill=12),
            make_player("Defender 1", skill=10),
            make_player("Defender 2", skill=10),
            make_player("Defender 3", skill=10),
            make_player("Inner Mid 1", skill=10),
            make_player("Inner Mid 2", skill=10),
            make_player("Inner Mid 3", skill=10),
            required_half,
            injured_competitor,
            make_player("Forward 1", skill=10),
            make_player("Forward 2", skill=10),
            make_player("Reserve 1", skill=8),
            make_player("Reserve 2", skill=8),
        ]
        service = self.service(players)

        result = service.analyze(
            self.csv_path,
            "Rival FC",
            ["3-5-2"],
            availability_mode=CURRENT_AVAILABLE,
            match_type=MATCH_TYPE_CUP,
            required_player_ids=(player_training_id(required_half),),
            training_rules=PlaymakingTrainingRules(),
            required_slot_classes={
                player_training_id(required_half): TrainingSlotClass.HALF_TRAINING.value,
                player_training_id(injured_competitor): TrainingSlotClass.HALF_TRAINING.value,
            },
        )

        lineup = {
            player.player_name: player
            for player in result.recommended_formation.lineup
        }
        self.assertIn("Required Half", lineup)
        self.assertEqual(lineup["Required Half"].position, "Winger (W)")
        self.assertNotIn("Injured Half Star", lineup)
        self.assertEqual(result.unavailable_players_count, 1)
        self.assertFalse(result.training_conflict_warning)


if __name__ == "__main__":
    unittest.main()
