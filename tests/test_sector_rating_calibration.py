import json
import tempfile
import unittest
from pathlib import Path

from engine.opponents.opponent_manager import OpponentManager
from engine.ratings import (
    ADVANTAGE_NOT_COMPARABLE,
    ADVANTAGE_OPPONENT,
    ADVANTAGE_OURS,
    SOURCE_HATTRICK_DECIMAL,
    SOURCE_HT_COACH_INTERNAL,
    build_sector_comparisons,
    detect_rating_scale,
    format_rating_value,
)
from ht_coach_app.services.match_workspace_service import (
    MatchAnalysisResult,
    MatchWorkspaceService,
    match_analysis_result_from_dict,
    match_analysis_result_to_dict,
)
from models.opponent import Opponent
from models.team_ratings import TeamRatings


class SectorRatingCalibrationTest(unittest.TestCase):
    def test_detects_hattrick_decimal_scale_without_changing_values(self):
        ratings = TeamRatings(
            left_defense=6.75,
            central_defense=7.25,
            right_defense=6.5,
            midfield=8.0,
            left_attack=5.5,
            central_attack=6.0,
            right_attack=5.75,
            indirect_defense=4.25,
            indirect_attack=5.0,
        )

        self.assertEqual(detect_rating_scale(ratings), SOURCE_HATTRICK_DECIMAL)
        self.assertEqual(format_rating_value(6.75, SOURCE_HATTRICK_DECIMAL), "6.75")
        self.assertEqual(format_rating_value(6.75, SOURCE_HATTRICK_DECIMAL, "es"), "6,75")

    def test_different_scales_are_not_directly_compared(self):
        our = TeamRatings(midfield=42, left_attack=26, right_defense=30)
        opponent = TeamRatings(midfield=7.25, right_defense=6.5, left_attack=5.5)

        comparisons = build_sector_comparisons(our, opponent)
        midfield = next(
            comparison for comparison in comparisons
            if comparison.matchup_key == "midfield"
        )

        self.assertFalse(midfield.comparable)
        self.assertIsNone(midfield.difference)
        self.assertEqual(midfield.advantage, ADVANTAGE_NOT_COMPARABLE)
        self.assertEqual(midfield.opponent_value, 7.25)

    def test_same_scale_comparison_uses_canonical_matchups(self):
        our = TeamRatings(left_attack=30, right_defense=25)
        opponent = TeamRatings(right_defense=26, left_attack=31)

        comparisons = build_sector_comparisons(
            our,
            opponent,
            opponent_scale=SOURCE_HT_COACH_INTERNAL,
        )
        our_left = next(
            comparison for comparison in comparisons
            if comparison.matchup_key == "our_left_attack"
        )
        opponent_left = next(
            comparison for comparison in comparisons
            if comparison.matchup_key == "opponent_left_attack"
        )

        self.assertEqual(our_left.our_sector, "left_attack")
        self.assertEqual(our_left.opponent_sector, "right_defense")
        self.assertEqual(our_left.difference, 4)
        self.assertEqual(our_left.advantage, ADVANTAGE_OURS)
        self.assertEqual(opponent_left.our_sector, "right_defense")
        self.assertEqual(opponent_left.opponent_sector, "left_attack")
        self.assertEqual(opponent_left.difference, -6)
        self.assertEqual(opponent_left.advantage, ADVANTAGE_OPPONENT)

    def test_opponent_persistence_round_trips_indirect_ratings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "opponents.json"
            manager = OpponentManager(path)
            manager.save(
                Opponent(
                    name="Pata2008",
                    ratings=TeamRatings(
                        left_defense=6.25,
                        central_defense=7.0,
                        right_defense=6.5,
                        midfield=7.5,
                        left_attack=5.75,
                        central_attack=6.0,
                        right_attack=5.5,
                        indirect_defense=4.5,
                        indirect_attack=5.25,
                    ),
                )
            )

            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw[0]["ratings"]["central_defense"], 7.0)
            self.assertEqual(raw[0]["ratings"]["indirect_attack"], 5.25)
            loaded = manager.get("Pata2008")
            self.assertEqual(loaded.ratings.indirect_defense, 4.5)

    def test_match_result_mapping_serializes_sector_comparisons(self):
        service = MatchWorkspaceService(None)
        mapped = service._map_results(
            [
                type(
                    "EngineResult",
                    (),
                    {
                        "formation": type("Formation", (), {"name": "3-5-2"})(),
                        "tactic": "Normal",
                        "tactic_level": 0,
                        "probabilities": type(
                            "Probabilities",
                            (),
                            {"win": 0.5, "draw": 0.3, "loss": 0.2},
                        )(),
                        "match_evaluation": type(
                            "Evaluation",
                            (),
                            {
                                "possession": 0.55,
                                "expected_goals": 2.0,
                                "opponent_expected_goals": 1.5,
                            },
                        )(),
                        "lineup": type("Lineup", (), {"players": []})(),
                        "ratings": TeamRatings(midfield=7.75),
                    },
                )()
            ],
            TeamRatings(midfield=7.25),
        )

        result = MatchAnalysisResult(
            player_count=0,
            opponent_name="Rival",
            formations=mapped,
            players_csv_filename="",
            analyzed_formations=["3-5-2"],
            completed_at="",
        )
        data = match_analysis_result_to_dict(result)
        restored = match_analysis_result_from_dict(data)

        self.assertEqual(
            restored.formations[0].sector_rating_comparisons[0].advantage,
            ADVANTAGE_OURS,
        )
        self.assertEqual(
            restored.formations[0].sector_rating_comparisons[0].difference,
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
