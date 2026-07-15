import unittest
import os


os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)


try:
    from PySide6.QtWidgets import QApplication

    from ht_coach_app.views.opponents_page import OpponentsPage
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise

    QApplication = None
    OpponentsPage = None


@unittest.skipIf(
    QApplication is None,
    "PySide6 is not installed"
)
class OpponentsPageSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_opponents_page_can_be_constructed(self):
        page = OpponentsPage()

        self.assertEqual(
            page.current_opponent_name(),
            None
        )
        self.assertIsNotNone(
            page.ratings_grid
        )


if __name__ == "__main__":
    unittest.main()
