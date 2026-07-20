import os
import tempfile
import unittest
from pathlib import Path

from engine.squad_evolution.age_policy import classify_age_band, normalize_age
from engine.squad_evolution.analyzer import SquadEvolutionAnalyzer
from engine.squad_evolution.models import (
    AGE_BAND_DEVELOPMENT,
    AGE_BAND_EXPERIENCED,
    AGE_BAND_LATE_CAREER,
    AGE_BAND_PRIME,
    AGE_BAND_UNKNOWN,
    AGE_BAND_VETERAN,
    HORIZON_MEDIUM_TERM,
    RISK_CRITICAL,
    RISK_HIGH,
    SUCCESSION_DEVELOPMENT,
    SUCCESSION_EMERGENCY,
    SUCCESSION_NEAR_READY,
    TRAINING_PLAYMAKING,
    TRAINING_UNKNOWN,
)
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
    MatchWorkspaceSettings,
)
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
)
from ht_coach_app.services.squad_builder_service import (
    IdealXIResult,
    PlayerContributionResult,
    SquadIdentityResult,
)
from ht_coach_app.services.squad_evolution_service import SquadEvolutionService
from models.player import Player


def make_player(name, age, days=0, injury=0, **skills):
    values = {
        "goalkeeper": 1,
        "defending": 1,
        "playmaking": 1,
        "winger": 1,
        "passing": 1,
        "scoring": 1,
        "set_pieces": 1,
    }
    values.update(skills)
    return Player(
        name=name,
        age=age,
        days=days,
        speciality="",
        form=8,
        stamina=8,
        experience=6,
        leadership=5,
        tsi=1000,
        salary=1000,
        injury=injury,
        injury_raw=str(injury),
        **values,
    )


def lineup_player(number, name, position):
    return LineupPlayerResult(
        number=number,
        position=position,
        side="CENTER",
        order="NORMAL",
        order_side="",
        player_name=name,
    )


def ideal_result(starters, identity=None):
    formation = FormationAnalysisResult(
        formation_name="3-5-2",
        recommended_tactic="Roster fit",
        tactic_level=0,
        win_probability=0,
        draw_probability=0,
        loss_probability=0,
        possession=0,
        expected_goals=0,
        opponent_expected_goals=0,
        lineup=[
            lineup_player(index + 1, name, position)
            for index, (name, position) in enumerate(starters)
        ],
        is_recommended=True,
    )
    return IdealXIResult(
        mode="Auto",
        selected_formation_name="3-5-2",
        best_formation_name="3-5-2",
        overall_score=100,
        confidence="High",
        reason="Test",
        formations=[formation, formation, formation],
        selected_formation=formation,
        squad_identity=identity or SquadIdentityResult(
            identity="Midfield Dominant Squad",
            explanation="Test",
            contributors=(PlayerContributionResult("Old Midfielder", "10"),),
        ),
    )


class SquadEvolutionTest(unittest.TestCase):
    def test_age_policy_boundaries_and_unknown_values(self):
        self.assertEqual(classify_age_band(17), AGE_BAND_DEVELOPMENT)
        self.assertEqual(classify_age_band(22), AGE_BAND_DEVELOPMENT)
        self.assertEqual(classify_age_band(23), AGE_BAND_PRIME)
        self.assertEqual(classify_age_band(29), AGE_BAND_EXPERIENCED)
        self.assertEqual(classify_age_band(32), AGE_BAND_VETERAN)
        self.assertEqual(classify_age_band(35), AGE_BAND_LATE_CAREER)
        self.assertEqual(classify_age_band("bad"), AGE_BAND_UNKNOWN)

        profile = normalize_age(type("P", (), {"age": 21, "days": 30})())
        self.assertEqual(profile.display_age, "21y 30d")
        self.assertEqual(profile.total_age_days, 2382)
        self.assertEqual(
            normalize_age(type("P", (), {"age": "bad"})()).age_band,
            AGE_BAND_UNKNOWN,
        )

    def test_starter_hierarchy_keeps_full_strength_starter_when_injured(self):
        players = [
            make_player("Old Defender", 34, injury=3, defending=18),
            make_player("Young Defender", 20, defending=17),
            make_player("Emergency Defender", 30, defending=6),
            make_player("Old Midfielder", 35, playmaking=18),
            make_player("Young Midfielder", 21, playmaking=13),
        ]
        full = ideal_result(
            [
                ("Old Defender", "Central Defender (CD)"),
                ("Old Midfielder", "Inner Midfielder (IM)"),
            ]
        )
        current = ideal_result(
            [
                ("Young Defender", "Central Defender (CD)"),
                ("Old Midfielder", "Inner Midfielder (IM)"),
            ]
        )

        result = SquadEvolutionAnalyzer().analyze(
            players,
            full_strength_result=full,
            current_available_result=current,
            planning_horizon=HORIZON_MEDIUM_TERM,
            training_focus=TRAINING_PLAYMAKING,
        )

        central_defense = next(
            row for row in result.succession_map if row.role == "Central Defense"
        )
        self.assertEqual(central_defense.full_strength_starter, "Old Defender")
        self.assertEqual(central_defense.current_available_starter, "Young Defender")
        self.assertTrue(central_defense.temporary_issue)
        self.assertIn(
            central_defense.succession_readiness,
            {SUCCESSION_NEAR_READY, SUCCESSION_DEVELOPMENT, SUCCESSION_EMERGENCY},
        )
        self.assertGreaterEqual(
            result.age_structure.average_full_strength_xi_age,
            result.age_structure.average_current_available_xi_age,
        )

    def test_training_alignment_and_priority_ranking_are_deterministic(self):
        players = [
            make_player("Only Keeper", 36, goalkeeper=18),
            make_player("Young Midfielder", 20, playmaking=14),
        ]
        full = ideal_result(
            [
                ("Only Keeper", "Goalkeeper (GK)"),
                ("Young Midfielder", "Inner Midfielder (IM)"),
            ]
        )
        result = SquadEvolutionAnalyzer().analyze(
            players,
            full_strength_result=full,
            current_available_result=full,
            training_focus=TRAINING_PLAYMAKING,
        )

        self.assertEqual(result.training_alignment.current_training, TRAINING_PLAYMAKING)
        self.assertIn("Goalkeeper", result.training_alignment.not_addressed)
        self.assertIn(result.priority_risks[0].risk_level, {RISK_HIGH, RISK_CRITICAL})
        self.assertEqual(
            [risk.role for risk in result.priority_risks],
            [risk.role for risk in SquadEvolutionAnalyzer().analyze(
                players,
                full_strength_result=full,
                current_available_result=full,
                training_focus=TRAINING_PLAYMAKING,
            ).priority_risks],
        )

    def test_training_focus_persistence_and_invalid_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            repository = MatchWorkspaceRepository(path)
            repository.save(
                MatchWorkspaceSettings(
                    players_csv_path="players.csv",
                    squad_training_focus=TRAINING_PLAYMAKING,
                    squad_planning_horizon=HORIZON_MEDIUM_TERM,
                )
            )
            settings = repository.load()
            self.assertEqual(settings.squad_training_focus, TRAINING_PLAYMAKING)
            self.assertEqual(settings.squad_planning_horizon, HORIZON_MEDIUM_TERM)

            service = SquadEvolutionService()
            self.assertEqual(
                service.normalize_training_focus("not-real"),
                TRAINING_UNKNOWN,
            )


@unittest.skipUnless(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    "Qt smoke test runs only in offscreen mode.",
)
class SquadEvolutionViewTest(unittest.TestCase):
    def test_evolution_tab_exists(self):
        from PySide6.QtWidgets import QApplication

        from ht_coach_app.views.squad_page import SquadPage

        app = QApplication.instance() or QApplication([])
        page = SquadPage()
        labels = [
            page.tabs.tabText(index)
            for index in range(page.tabs.count())
        ]
        self.assertIn("Evolution", labels)
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
