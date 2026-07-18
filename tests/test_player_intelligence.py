import os
import unittest
from dataclasses import FrozenInstanceError

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ht_coach_app.player_intelligence.alternative_analyzer import (
    COMPETITIVE_THRESHOLD,
    EFFECTIVE_TIE_THRESHOLD,
)
from ht_coach_app.player_intelligence.profile_classifier import (
    PlayerProfileClassifier,
)
from ht_coach_app.player_intelligence.service import (
    PlayerIntelligenceService,
)
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
)
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
)
from models.player import Player
from models.position import Position


def make_player(
    name,
    goalkeeper=1,
    defending=5,
    playmaking=5,
    winger=5,
    passing=5,
    scoring=5,
    form=7,
    stamina=7,
    experience=5,
):
    return Player(
        name=name,
        age=25,
        days=0,
        speciality="",
        form=form,
        stamina=stamina,
        goalkeeper=goalkeeper,
        defending=defending,
        playmaking=playmaking,
        winger=winger,
        passing=passing,
        scoring=scoring,
        set_pieces=4,
        experience=experience,
        leadership=4,
        tsi=1000,
        salary=1000,
    )


def formation_result_with_players(
    formation_name,
    players_by_slot,
):
    lineup = []
    for index, slot in enumerate(get_formation_layout(formation_name)):
        name = players_by_slot.get(slot.position, f"Filler {index}")
        lineup.append(
            LineupPlayerResult(
                number=index + 1,
                position=slot.position_label,
                side=slot.side,
                order="Normal",
                order_side="",
                player_name=name,
            )
        )

    return FormationAnalysisResult(
        formation_name=formation_name,
        recommended_tactic="Pressing",
        tactic_level=7.0,
        win_probability=0.55,
        draw_probability=0.25,
        loss_probability=0.20,
        possession=0.60,
        expected_goals=2.0,
        opponent_expected_goals=1.0,
        lineup=lineup,
        is_recommended=True,
    )


class PlayerProfileClassifierTest(unittest.TestCase):
    def setUp(self):
        self.classifier = PlayerProfileClassifier()

    def test_profile_classification_for_supported_positions(self):
        cases = [
            (
                make_player("Keeper", goalkeeper=10, defending=4),
                Position.GOALKEEPER.value,
                "Shot Stopper",
            ),
            (
                make_player("Defender", defending=10, playmaking=4),
                Position.CENTRAL_DEFENDER.value,
                "Defensive Anchor",
            ),
            (
                make_player("Wing Back", defending=9, winger=4),
                Position.WING_BACK.value,
                "Defensive Fullback",
            ),
            (
                make_player("Mid", playmaking=10, defending=5, passing=5),
                Position.INNER_MIDFIELDER.value,
                "Playmaker",
            ),
            (
                make_player("Winger", winger=10, defending=4),
                Position.WINGER.value,
                "Attacking Winger",
            ),
            (
                make_player("Forward", scoring=10, passing=4),
                Position.FORWARD.value,
                "Primary Finisher",
            ),
        ]

        for player, position, expected in cases:
            with self.subTest(position=position):
                label, _ = self.classifier.classify(player, position)
                self.assertEqual(label, expected)

    def test_classification_boundary_uses_modest_labels(self):
        label, summary = self.classifier.classify(
            make_player(
                "Balanced",
                defending=6,
                playmaking=6,
                passing=6,
                scoring=6,
            ),
            Position.INNER_MIDFIELDER.value,
        )

        self.assertEqual(label, "Box-to-Box Midfielder")
        self.assertNotIn("elite", summary.lower())


class PlayerIntelligenceServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = PlayerIntelligenceService()

    def _forward_board_player(self, selected_name="Rushton"):
        result = formation_result_with_players(
            "3-5-2",
            {Position.FORWARD.value: selected_name},
        )
        board = FormationBoardMapper().to_board(result)
        return next(
            slot.player
            for slot in board.slots
            if slot.player.player_name == selected_name
        )

    def test_strengths_limitations_and_item_limits(self):
        player = make_player(
            "Rushton",
            scoring=10,
            passing=8,
            playmaking=8,
            stamina=4,
            form=9,
        )
        view_model = self.service.analyze(
            self._forward_board_player(),
            [player],
        )

        self.assertLessEqual(len(view_model.strengths), 4)
        self.assertTrue(
            any("scoring" in point.title.lower() for point in view_model.strengths)
        )
        self.assertTrue(
            any("stamina" in point.title.lower() for point in view_model.limitations)
        )
        self.assertFalse(
            any("chemistry" in point.detail.lower() for point in view_model.strengths)
        )

    def test_neutral_player_does_not_receive_misleading_criticism(self):
        player = make_player(
            "Rushton",
            defending=1,
            playmaking=5,
            winger=1,
            passing=6,
            scoring=6,
        )
        view_model = self.service.analyze(
            self._forward_board_player(),
            [player],
        )

        self.assertFalse(view_model.limitations)

    def test_missing_data_is_safe(self):
        view_model = self.service.analyze(
            self._forward_board_player(),
            [],
        )

        self.assertEqual(view_model.availability_state, "unavailable")
        self.assertIn("unavailable", view_model.headline)

    def test_why_selected_verified_best_candidate_and_close_alternative(self):
        selected = make_player("Rushton", scoring=10, passing=7)
        close = make_player("Romualdo", scoring=10, passing=7)
        view_model = self.service.analyze(
            self._forward_board_player(),
            [selected, close],
        )

        self.assertTrue(
            any("Highest evaluated" in point.title for point in view_model.why_selected)
        )
        self.assertTrue(
            any("close" in alt.reason_not_selected.lower() for alt in view_model.alternatives)
        )

    def test_tactical_contributions_are_normalized_without_probability_wording(self):
        selected = make_player("Rushton", scoring=10, passing=8)
        alternative = make_player("Romualdo", scoring=5, passing=5)
        view_model = self.service.analyze(
            self._forward_board_player(),
            [selected, alternative],
        )

        self.assertTrue(view_model.tactical_contributions)
        for contribution in view_model.tactical_contributions:
            self.assertGreaterEqual(contribution.normalized_value, 0.0)
            self.assertLessEqual(contribution.normalized_value, 1.0)
            self.assertNotIn(
                "probability",
                contribution.interpretation.lower(),
            )

    def test_alternatives_are_same_role_deterministic_and_limited(self):
        selected = make_player("Rushton", scoring=10, passing=7)
        players = [
            selected,
            make_player("A", scoring=9, passing=7),
            make_player("B", scoring=8, passing=7),
            make_player("C", scoring=7, passing=7),
            make_player("D", scoring=6, passing=7),
        ]
        first = self.service.analyze(
            self._forward_board_player(),
            players,
        )
        second = self.service.analyze(
            self._forward_board_player(),
            players,
        )

        self.assertEqual(len(first.alternatives), 3)
        self.assertNotIn(
            "Rushton",
            [alternative.player_name for alternative in first.alternatives],
        )
        self.assertEqual(first.alternatives, second.alternatives)
        self.assertTrue(
            all(
                "win" not in alternative.reason_not_selected.lower()
                for alternative in first.alternatives
            )
        )

    def test_empty_alternative_list(self):
        selected = make_player("Rushton", scoring=10)
        view_model = self.service.analyze(
            self._forward_board_player(),
            [selected],
        )

        self.assertEqual(view_model.alternatives, ())
        self.assertIn("No same-role alternative", view_model.headline)

    def test_view_models_are_immutable_and_serializable_by_shape(self):
        selected = make_player("Rushton", scoring=10)
        view_model = self.service.analyze(
            self._forward_board_player(),
            [selected],
        )

        with self.assertRaises(FrozenInstanceError):
            view_model.player_name = "Changed"

        self.assertIsInstance(view_model.technical_attributes, tuple)

    def test_threshold_constants_are_documented_values(self):
        self.assertEqual(EFFECTIVE_TIE_THRESHOLD, 0.25)
        self.assertEqual(COMPETITIVE_THRESHOLD, 1.0)


try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel

    from ht_coach_app.widgets.formation_board.formation_board import (
        FormationBoard,
    )
    from ht_coach_app.widgets.formation_board.player_card import PlayerCard
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    FormationBoard = None
    PlayerCard = None
    QLabel = None
    QTest = None
    Qt = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class PlayerIntelligenceFormationBoardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_click_selection_updates_intelligence_inspector(self):
        result = formation_result_with_players(
            "3-5-2",
            {Position.FORWARD.value: "Rushton"},
        )
        board_model = FormationBoardMapper().to_board(result)
        board_widget = FormationBoard()
        board_widget.set_boards(
            [board_model],
            roster_players=[
                make_player("Rushton", scoring=10, passing=5),
                make_player("Romualdo", scoring=8, passing=7),
            ],
        )

        card = next(
            card
            for card in board_widget.findChildren(PlayerCard)
            if card.player.player_name == "Rushton"
        )
        card.click()

        labels = [
            label.text()
            for label in board_widget.findChildren(QLabel)
        ]
        self.assertIn("Why Recommended", labels)
        self.assertTrue(
            any("Primary Finisher" in label for label in labels)
        )

    def test_keyboard_selection_updates_intelligence_inspector(self):
        result = formation_result_with_players(
            "3-5-2",
            {Position.FORWARD.value: "Rushton"},
        )
        board_model = FormationBoardMapper().to_board(result)
        board_widget = FormationBoard()
        board_widget.set_boards(
            [board_model],
            roster_players=[make_player("Rushton", scoring=10)],
        )
        card = next(
            card
            for card in board_widget.findChildren(PlayerCard)
            if card.player.player_name == "Rushton"
        )

        card.setFocus()
        QTest.keyClick(card, Qt.Key_Space)
        QApplication.processEvents()

        self.assertEqual(
            board_widget.current_board().selected_player.player_name,
            "Rushton",
        )

    def test_clear_selection_resets_inspector(self):
        result = formation_result_with_players(
            "3-5-2",
            {Position.FORWARD.value: "Rushton"},
        )
        board_model = FormationBoardMapper().to_board(result)
        board_widget = FormationBoard()
        board_widget.set_boards(
            [board_model],
            roster_players=[make_player("Rushton", scoring=10)],
        )
        player_id = board_model.slots[0].player.player_id
        board_widget.select_player(player_id)
        board_widget.clear_selection()

        labels = [
            label.text()
            for label in board_widget.findChildren(QLabel)
        ]
        self.assertIn(
            "Select a player on the pitch to inspect details.",
            labels,
        )

    def test_switching_formation_clears_invalid_selection(self):
        first = FormationBoardMapper().to_board(
            formation_result_with_players(
                "3-5-2",
                {Position.FORWARD.value: "Rushton"},
            )
        )
        second = FormationBoardMapper().to_board(
            formation_result_with_players(
                "4-5-1",
                {Position.FORWARD.value: "Romualdo"},
            )
        )
        board_widget = FormationBoard()
        board_widget.set_boards(
            [first, second],
            roster_players=[
                make_player("Rushton", scoring=10),
                make_player("Romualdo", scoring=8),
            ],
        )
        board_widget.select_player(first.slots[0].player.player_id)
        board_widget.formation_combo.setCurrentIndex(1)

        self.assertEqual(
            board_widget.current_board().selected_player_id,
            "",
        )

    def test_restored_incomplete_result_shows_unavailable_state(self):
        board_model = FormationBoardMapper().to_board(
            formation_result_with_players(
                "3-5-2",
                {Position.FORWARD.value: "Rushton"},
            )
        )
        board_widget = FormationBoard()
        board_widget.set_boards([board_model], roster_players=[])
        board_widget.select_player(board_model.slots[0].player.player_id)

        labels = [
            label.text()
            for label in board_widget.findChildren(QLabel)
        ]
        self.assertTrue(
            any("unavailable" in label.lower() for label in labels)
        )


if __name__ == "__main__":
    unittest.main()
