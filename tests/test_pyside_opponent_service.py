import json
import tempfile
import unittest
from pathlib import Path

from ht_coach_app.persistence.opponent_repository import OpponentRepository
from ht_coach_app.services.opponent_service import (
    DEFAULT_RATINGS,
    OpponentService,
    OpponentValidationError,
    RATING_FIELDS,
)


class OpponentServiceTest(unittest.TestCase):
    def setUp(self):
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
        self.temp_dir.cleanup()

    def test_create_persists_opponent_to_json(self):
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

    def test_update_can_rename_existing_opponent(self):
        self.service.create_opponent(
            "Rival FC",
            DEFAULT_RATINGS
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

