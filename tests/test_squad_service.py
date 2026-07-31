import tempfile
import unittest
from pathlib import Path

from models.player import Player
from models.player_score import PlayerScore
from ht_coach_app.services.squad_service import (
    SquadService,
    SquadValidationError,
)


class FakeAnalyzer:
    @staticmethod
    def best_position(player):
        if player.name == "Alice":
            return ("INNER_MIDFIELDER", 42.0)

        return ("GOALKEEPER", 38.0)

    @staticmethod
    def rank_players(players, position, side=None):
        scores = []

        for player in players:
            if position == "GOALKEEPER":
                score = player.goalkeeper * 10
            else:
                score = player.playmaking * 10

            scores.append(
                PlayerScore(
                    player=player,
                    score=score
                )
            )

        return sorted(
            scores,
            key=lambda item: item.score,
            reverse=True
        )


def make_player(name, form, stamina, speciality, goalkeeper, playmaking):
    return Player(
        name=name,
        age=22,
        days=10,
        speciality=speciality,
        form=form,
        stamina=stamina,
        goalkeeper=goalkeeper,
        defending=5,
        playmaking=playmaking,
        winger=6,
        passing=7,
        scoring=8,
        set_pieces=3,
        experience=4,
        leadership=5,
        tsi=1234,
        salary=567,
    )


class SquadServiceTest(unittest.TestCase):
    def setUp(self):
        self.players = [
            make_player("Alice", 7, 8, "Quick", 2, 9),
            make_player("Bob", 5, 6, "", 8, 4),
            make_player("Carlos", 3, 9, "Powerful", 3, 7),
        ]
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "players.csv"
        self.csv_path.write_text(
            "placeholder",
            encoding="utf-8"
        )
        self.service = SquadService(
            importer=lambda _path: list(self.players),
            analyzer=FakeAnalyzer
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_roster_maps_players(self):
        from models.specialty import Specialty

        roster = self.service.load_roster(
            self.csv_path
        )

        self.assertEqual(roster.player_count, 3)
        self.assertEqual(roster.rows[0].name, "Alice")
        self.assertEqual(roster.rows[0].tsi, 1234)
        self.assertEqual(roster.specialties, (Specialty.QUICK, Specialty.POWERFUL))

    def test_missing_csv_raises_user_safe_error(self):
        with self.assertRaises(SquadValidationError):
            self.service.load_roster(
                Path(self.temp_dir.name) / "missing.csv"
            )

    def test_filters_and_name_search(self):
        rows = self.service.map_players(
            self.players,
            selected_position="Inner Midfielder (IM)"
        )

        filtered = self.service.filter_rows(
            rows,
            search_text="ali",
            minimum_form=6,
            minimum_stamina=8,
            speciality="Quick",
            selected_position="Inner Midfielder (IM)"
        )

        self.assertEqual(
            [row.name for row in filtered],
            ["Alice"]
        )

    def test_position_ranking_uses_existing_analyzer(self):
        rows = self.service.map_players(
            self.players,
            selected_position="Goalkeeper (GK)"
        )
        bob = next(row for row in rows if row.name == "Bob")

        self.assertEqual(bob.selected_position_rank, 1)
        self.assertEqual(bob.selected_position_score, 80)

    def test_export_visible_rows_to_csv(self):
        rows = self.service.map_players(
            self.players,
            selected_position="Goalkeeper (GK)"
        )
        export_path = Path(self.temp_dir.name) / "visible.csv"

        self.service.export_rows_to_csv(
            rows[:1],
            export_path
        )

        content = export_path.read_text(
            encoding="utf-8"
        )

        self.assertIn("name,age,form", content)
        self.assertIn("Alice", content)

    def test_importer_errors_are_normalized(self):
        service = SquadService(
            importer=lambda _path: (_ for _ in ()).throw(ValueError("bad csv")),
            analyzer=FakeAnalyzer
        )

        with self.assertRaisesRegex(SquadValidationError, "Could not load"):
            service.load_roster(
                self.csv_path
            )


if __name__ == "__main__":
    unittest.main()
