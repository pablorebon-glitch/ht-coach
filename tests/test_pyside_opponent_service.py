import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from engine.calendar import HTCalendarService
from ht_coach_app.services import ht_week_context_provider
from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.opponent_service import (
    DEFAULT_RATINGS,
    OpponentService,
    OpponentValidationError,
    RATING_FIELDS,
)
from models.opponent import Opponent
from models.team_ratings import TeamRatings


class OpponentServiceTest(unittest.TestCase):
    def setUp(self):
        self.original_calendar_service = ht_week_context_provider.get_calendar_service()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = (
            Path(self.temp_dir.name)
            / "opponents.json"
        )
        self.repository = OpponentRepository(
            self.storage_path
        )
        self.service = OpponentService(
            self.repository
        )

    def tearDown(self):
        ht_week_context_provider.set_calendar_service(self.original_calendar_service)
        self.temp_dir.cleanup()

    def test_create_persists_opponent_to_json(self):
        ht_week_context_provider.set_calendar_service(
            HTCalendarService(clock=lambda: datetime(2026, 8, 20, 12, 0, 0))
        )
        opponent = self.service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )

        saved_data = json.loads(
            self.storage_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            opponent.name,
            "Rival FC"
        )
        self.assertEqual(
            saved_data[0]["name"],
            "Rival FC"
        )
        self.assertEqual(
            saved_data[0]["ratings"]["midfield"],
            DEFAULT_RATINGS["midfield"]
        )
        self.assertEqual(
            saved_data[0]["created_at"],
            "2026-08-20T12:00:00"
        )

    def test_list_opponents_by_recency_returns_recently_created_first(self):
        self.repository.save(
            Opponent(
                name="Opponent A",
                ratings=TeamRatings(),
                created_at="2026-07-01T00:00:00",
            )
        )
        self.repository.save(
            Opponent(
                name="Opponent B",
                ratings=TeamRatings(),
                created_at="2026-08-20T00:00:00",
            )
        )
        self.repository.save(
            Opponent(
                name="Opponent C",
                ratings=TeamRatings(),
                created_at="2026-08-10T00:00:00",
            )
        )

        self.assertEqual(
            [opponent.name for opponent in self.service.list_opponents_by_recency()],
            ["Opponent B", "Opponent C", "Opponent A"],
        )

    def test_list_opponents_returns_manual_order_with_new_entries_first(self):
        self.service.create_opponent(
            "Opponent A",
            DEFAULT_RATINGS
        )
        self.service.create_opponent(
            "Opponent B",
            DEFAULT_RATINGS
        )

        self.assertEqual(
            [opponent.name for opponent in self.service.list_opponents()],
            ["Opponent B", "Opponent A"],
        )

    def test_move_opponent_up_and_down_uses_manual_order(self):
        self.service.create_opponent("Opponent A", DEFAULT_RATINGS)
        self.service.create_opponent("Opponent B", DEFAULT_RATINGS)
        self.service.create_opponent("Opponent C", DEFAULT_RATINGS)

        self.assertTrue(self.service.move_opponent_down("Opponent C"))
        self.assertEqual(
            [opponent.name for opponent in self.service.list_opponents()],
            ["Opponent B", "Opponent C", "Opponent A"],
        )

        self.assertTrue(self.service.move_opponent_up("Opponent A"))
        self.assertEqual(
            [opponent.name for opponent in self.service.list_opponents()],
            ["Opponent B", "Opponent A", "Opponent C"],
        )

    def test_update_can_rename_existing_opponent(self):
        ht_week_context_provider.set_calendar_service(
            HTCalendarService(clock=lambda: datetime(2026, 8, 20, 12, 0, 0))
        )
        self.service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )
        created_at = self.service.get_opponent("Rival FC").created_at
        ht_week_context_provider.set_calendar_service(
            HTCalendarService(clock=lambda: datetime(2026, 8, 24, 12, 0, 0))
        )

        updated = self.service.update_opponent(
            "Rival FC",
            "Renamed FC",
            {
                **DEFAULT_RATINGS,
                "midfield": 45
            }
        )

        self.assertEqual(
            updated.name,
            "Renamed FC"
        )
        self.assertIsNone(
            self.service.get_opponent("Rival FC")
        )
        self.assertEqual(
            self.service.get_opponent("Renamed FC").ratings.midfield,
            45
        )
        self.assertEqual(
            self.service.get_opponent("Renamed FC").created_at,
            created_at
        )

    def test_delete_removes_existing_opponent(self):
        self.service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )

        self.service.delete_opponent(
            "Rival FC"
        )

        self.assertEqual(
            self.service.list_opponents(),
            []
        )

    def test_duplicate_creates_unique_copy_name(self):
        self.service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
        )
        self.service.duplicate_opponent(
            "Rival FC"
        )
        duplicate = self.service.duplicate_opponent(
            "Rival FC"
        )

        self.assertEqual(
            duplicate.name,
            "Rival FC Copy 2"
        )
        self.assertEqual(
            len(self.service.list_opponents()),
            3
        )

    def test_name_is_required(self):
        with self.assertRaises(OpponentValidationError):
            self.service.create_opponent(
                " ",
                DEFAULT_RATINGS
            )

    def test_all_ratings_are_required(self):
        ratings = dict(DEFAULT_RATINGS)
        ratings.pop("midfield")

        with self.assertRaises(OpponentValidationError):
            self.service.create_opponent(
                "Rival FC",
                ratings
            )

    def test_ratings_must_be_numeric(self):
        for field in RATING_FIELDS:
            with self.subTest(field=field):
                ratings = dict(DEFAULT_RATINGS)
                ratings[field] = "not numeric"

                with self.assertRaises(OpponentValidationError):
                    self.service.create_opponent(
                        f"Rival {field}",
                        ratings
                    )

    def test_ratings_must_be_zero_or_greater(self):
        ratings = {
            **DEFAULT_RATINGS,
            "left_defense": -1
        }

        with self.assertRaises(OpponentValidationError):
            self.service.create_opponent(
                "Rival FC",
                ratings
            )


if __name__ == "__main__":
    unittest.main()
