import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from engine.weekly_training.models import TrainingSlotClass
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_rules import PlaymakingTrainingRules
from ht_coach_app.services.match_workspace_service import (
    MATCH_TYPE_CUP,
    MATCH_TYPE_FRIENDLY,
    MATCH_TYPE_LEAGUE,
    MatchWorkspaceService,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)
from ht_coach_app.views.match_page import MatchPage
from models.opponent import Opponent
from models.player import Player
from models.team_ratings import TeamRatings


class FakeOpponentService:
    def __init__(self):
        self.opponent = Opponent(
            name="Santa Cruz Club",
            ratings=TeamRatings(
                left_defense=8,
                central_defense=8,
                right_defense=8,
                midfield=8,
                left_attack=8,
                central_attack=8,
                right_attack=8,
            ),
        )

    def get_opponent(self, name):
        return self.opponent if name == self.opponent.name else None

    def list_opponents(self):
        return [self.opponent]


def make_player(name, skill=8, injury=0):
    return Player(
        name=name,
        age=24,
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
        injury_raw=str(injury),
    )


def rotation_squad():
    starters = [make_player(f"Starter {index}", 18) for index in range(1, 12)]
    reserves = [make_player(f"Reserve {index}", 10) for index in range(1, 12)]
    return starters + reserves, starters, reserves


class CompetitionAwarePolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "players.csv"
        self.csv_path.write_text("placeholder", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def service(self, players):
        return MatchWorkspaceService(
            FakeOpponentService(),
            importer=lambda _path: players,
        )

    def analyze(self, players, match_type, match_1_ids=(), required_ids=(), slot_classes=None):
        return self.service(players).analyze(
            self.csv_path,
            "Santa Cruz Club",
            ["3-5-2"],
            match_type=match_type,
            training_rules=PlaymakingTrainingRules(),
            required_player_ids=tuple(required_ids),
            required_slot_classes=slot_classes or {},
            match_1_player_ids=tuple(match_1_ids),
        )

    def test_cup_and_friendly_use_different_policy_for_same_fixture(self):
        players, starters, reserves = rotation_squad()
        match_1_ids = {player_training_id(player) for player in starters}

        cup = self.analyze(players, MATCH_TYPE_CUP, match_1_ids=match_1_ids)
        friendly = self.analyze(players, MATCH_TYPE_FRIENDLY, match_1_ids=match_1_ids)

        cup_names = {player.player_name for player in cup.recommended_formation.lineup}
        friendly_names = {player.player_name for player in friendly.recommended_formation.lineup}
        reserve_names = {player.name for player in reserves}

        self.assertEqual(cup.selection_policy, "competitive")
        self.assertEqual(friendly.selection_policy, "friendly_rotation")
        self.assertNotEqual(cup_names, friendly_names)
        self.assertLess(
            friendly.rotation_summary["unnecessary_repeat_count"],
            len(cup_names & {player.name for player in starters}),
        )
        self.assertEqual(friendly_names, reserve_names)

    def test_league_and_friendly_use_different_policy_for_same_fixture(self):
        players, starters, _reserves = rotation_squad()
        match_1_ids = {player_training_id(player) for player in starters}

        league = self.analyze(players, MATCH_TYPE_LEAGUE, match_1_ids=match_1_ids)
        friendly = self.analyze(players, MATCH_TYPE_FRIENDLY, match_1_ids=match_1_ids)

        self.assertEqual(league.selection_policy, "competitive")
        self.assertEqual(friendly.selection_policy, "friendly_rotation")
        self.assertLess(
            friendly.rotation_summary["unnecessary_repeat_count"],
            len({player.player_name for player in league.recommended_formation.lineup}),
        )

    def test_required_50_outstanding_repeat_beats_friendly_rotation(self):
        required_half = make_player("Required Half", 6)
        players, starters, _reserves = rotation_squad()
        players = [required_half] + players
        match_1_ids = {player_training_id(player) for player in starters}
        match_1_ids.add(player_training_id(required_half))

        result = self.analyze(
            players,
            MATCH_TYPE_FRIENDLY,
            match_1_ids=match_1_ids,
            required_ids={player_training_id(required_half)},
            slot_classes={
                player_training_id(required_half): TrainingSlotClass.HALF_TRAINING.value,
            },
        )

        lineup = {player.player_name: player for player in result.recommended_formation.lineup}
        self.assertIn("Required Half", lineup)
        self.assertEqual(lineup["Required Half"].position, "Winger (W)")
        self.assertIn(
            player_training_id(required_half),
            result.rotation_summary["required_repeat_player_ids"],
        )

    def test_friendly_without_match_1_context_does_not_invent_repetition(self):
        players, _starters, _reserves = rotation_squad()

        result = self.analyze(players, MATCH_TYPE_FRIENDLY)

        self.assertFalse(result.rotation_summary["match_1_context_available"])
        self.assertEqual(result.rotation_summary["repeat_count"], 0)
        self.assertEqual(result.rotation_summary["unnecessary_repeat_count"], 0)

    def test_result_serialization_preserves_friendly_policy(self):
        players, starters, _reserves = rotation_squad()
        match_1_ids = {player_training_id(player) for player in starters}
        result = self.analyze(players, MATCH_TYPE_FRIENDLY, match_1_ids=match_1_ids)

        restored = match_analysis_result_from_dict(
            match_analysis_result_to_dict(result)
        )

        self.assertEqual(restored.match_type, MATCH_TYPE_FRIENDLY)
        self.assertEqual(restored.selection_policy, "friendly_rotation")
        self.assertEqual(
            restored.rotation_summary["match_1_player_ids"],
            result.rotation_summary["match_1_player_ids"],
        )


def test_match_page_competition_selector_exposes_three_sporting_options():
    app = QApplication.instance() or QApplication([])
    page = MatchPage()

    assert page.match_type_combo.findData(MATCH_TYPE_LEAGUE) >= 0
    assert page.match_type_combo.findData(MATCH_TYPE_CUP) >= 0
    assert page.match_type_combo.findData(MATCH_TYPE_FRIENDLY) >= 0
    assert [
        page.match_type_combo.itemData(index)
        for index in range(page.match_type_combo.count())
    ] == ["", MATCH_TYPE_LEAGUE, MATCH_TYPE_CUP, MATCH_TYPE_FRIENDLY]
    page.deleteLater()
    app.processEvents()
