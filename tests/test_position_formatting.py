import unittest

from ht_coach_app.core.position_formatting import (
    format_position,
    format_position_abbreviation,
    format_position_name,
)
from models.position import Position


class PositionFormattingTest(unittest.TestCase):
    def test_formats_every_supported_position(self):
        expected = {
            Position.GOALKEEPER: ("Goalkeeper", "GK", "Goalkeeper (GK)"),
            Position.CENTRAL_DEFENDER: (
                "Central Defender",
                "CD",
                "Central Defender (CD)",
            ),
            Position.WING_BACK: ("Wing Back", "WB", "Wing Back (WB)"),
            Position.INNER_MIDFIELDER: (
                "Inner Midfielder",
                "IM",
                "Inner Midfielder (IM)",
            ),
            Position.WINGER: ("Winger", "W", "Winger (W)"),
            Position.FORWARD: ("Forward", "F", "Forward (F)"),
        }

        for position, values in expected.items():
            with self.subTest(position=position):
                name, abbreviation, label = values

                self.assertEqual(
                    format_position_name(position),
                    name
                )
                self.assertEqual(
                    format_position_abbreviation(position),
                    abbreviation
                )
                self.assertEqual(
                    format_position(position),
                    label
                )

    def test_unknown_position_falls_back_to_title_case(self):
        self.assertEqual(
            format_position("LEFT_CENTER_BACK"),
            "Left Center Back"
        )

    def test_already_formatted_position_is_preserved(self):
        self.assertEqual(
            format_position("Goalkeeper (GK)"),
            "Goalkeeper (GK)"
        )


if __name__ == "__main__":
    unittest.main()
