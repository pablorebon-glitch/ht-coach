import os
import unittest

from ht_coach_app.services.squad_service import PlayerRow


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)


try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from ht_coach_app.views.squad_page import SquadPage
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    Qt = None
    SquadPage = None


def make_row(
    name,
    tsi,
    selected_position_score=0.0,
    selected_position_rank=0,
    speciality="",
    best_position="Goalkeeper (GK)"
):
    return PlayerRow(
        name=name,
        age=25,
        form=7,
        stamina=8,
        experience=6,
        leadership=5,
        tsi=tsi,
        salary=1000,
        goalkeeper=4,
        defending=5,
        playmaking=6,
        winger=7,
        passing=8,
        scoring=9,
        set_pieces=10,
        speciality=speciality,
        selected_position_score=selected_position_score,
        selected_position_rank=selected_position_rank,
        best_position=best_position,
    )


@unittest.skipIf(
    QApplication is None,
    "PySide6 is not installed"
)
class SquadTableSortingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = SquadPage()

    def _column_values(self, column):
        return [
            self.page.players_table.item(row, column).text()
            for row in range(self.page.players_table.rowCount())
        ]

    def test_tsi_sorts_numerically_descending(self):
        self.page.set_players(
            [
                make_row("Lower TSI", 3220),
                make_row("Higher TSI", 10920),
            ]
        )

        self.page.players_table.sortItems(
            6,
            Qt.DescendingOrder
        )

        self.assertEqual(
            self._column_values(6),
            ["10920", "3220"]
        )

    def test_tsi_sorts_numerically_ascending(self):
        self.page.set_players(
            [
                make_row("Higher TSI", 10920),
                make_row("Lower TSI", 3220),
            ]
        )

        self.page.players_table.sortItems(
            6,
            Qt.AscendingOrder
        )

        self.assertEqual(
            self._column_values(6),
            ["3220", "10920"]
        )

    def test_decimal_position_scores_sort_numerically(self):
        self.page.set_players(
            [
                make_row("Ten Point Two", 5000, 10.2, 2),
                make_row("Nine Point Eight", 5000, 9.8, 1),
            ]
        )

        self.page.players_table.sortItems(
            16,
            Qt.AscendingOrder
        )

        self.assertEqual(
            self._column_values(16),
            ["9.80", "10.20"]
        )

    def test_text_columns_sort_alphabetically(self):
        self.page.set_players(
            [
                make_row("Carlos", 5000, speciality="Quick"),
                make_row("Alice", 5000, speciality="Powerful"),
                make_row("Bob", 5000, speciality="Technical"),
            ]
        )

        self.page.players_table.sortItems(
            0,
            Qt.AscendingOrder
        )

        self.assertEqual(
            self._column_values(0),
            ["Alice", "Bob", "Carlos"]
        )

    def test_empty_numeric_values_sort_without_crashing(self):
        self.page.set_players(
            [
                make_row("Ranked", 5000, 10.0, 1),
                make_row("Unranked", 5000, 0.0, 0),
            ]
        )

        self.page.players_table.sortItems(
            17,
            Qt.AscendingOrder
        )

        self.assertEqual(
            self._column_values(17),
            ["", "1"]
        )


if __name__ == "__main__":
    unittest.main()
