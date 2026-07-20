import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QApplication

from engine.ratings.sector_rating import MATCHUP_PAIRS
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.opponent_ratings_clipboard_parser import (
    MAX_CLIPBOARD_LENGTH,
    parse_opponent_ratings_clipboard,
)
from ht_coach_app.services.opponent_service import (
    ALL_RATING_FIELDS,
    HATTRICK_SECTOR_ORDER,
)
from ht_coach_app.views.opponents_page import OpponentsPage
from ht_coach_app.widgets.decimal_spin_box import DecimalSpinBox


SPANISH_FIXTURE = """[table][tr][th][matchid=764960153][/th][th colspan=2]pata2008 [teamid=109910][/th][/tr]
[tr][th]Mediocampo[/th][td]insuficiente - bajo[/td][td align=right]5,25[/td][/tr]
[tr][th]Defensa derecha[/th][td]aceptable - muy alto[/td][td align=right]6,75[/td][/tr]
[tr][th]Defensa central[/th][td]bueno - muy bajo[/td][td align=right]7,00[/td][/tr]
[tr][th]Defensa izquierda[/th][td]insuficiente - alto[/td][td align=right]5,50[/td][/tr]
[tr][th]Ataque derecho[/th][td]insuficiente - bajo[/td][td align=right]5,25[/td][/tr]
[tr][th]Ataque central[/th][td]debil - alto[/td][td align=right]4,50[/td][/tr]
[tr][th]Ataque izquierdo[/th][td]debil - muy bajo[/td][td align=right]4,00[/td][/tr]
[tr][th colspan=3]Tiro indirecto[/th][/tr]
[tr][th]Defensa[/th][td]bueno - muy bajo[/td][td align=right]7,00[/td][/tr]
[tr][th]Ataque[/th][td]aceptable - alto[/td][td align=right]6,50[/td][/tr]
[tr][th colspan=3]Plan de juego[/th][/tr]
[tr][th]Actitud del equipo[/th][td colspan=2](Oculta)[/td][/tr]
[tr][th]Tactica[/th][td colspan=2]Normal[/td][/tr]
[tr][th]Nivel de tactica[/th][td colspan=2](---)[/td][/tr]
[tr][th]Estilo de juego[/th][td colspan=2]neutro[/td][/tr]
[tr][th colspan=3]Calificaciones medias[/th][/tr]
[tr][th]Experiencia total de los jugadores[/th][td]insuficiente - bajo[/td][td align=right]5,25[/td][/tr]
[tr][th]Mediocampo promedio[/th][td]insuficiente - bajo[/td][td align=right]9,99[/td][/tr]
[tr][th]Defensa promedio[/th][td]aceptable - alto[/td][td align=right]8,88[/td][/tr]
[tr][th]Ataque promedio[/th][td]debil - muy alto[/td][td align=right]4,75[/td][/tr]
[tr][th]Promedio total[/th][td]insuficiente - alto[/td][td align=right]5,50[/td][/tr]
[/table]"""


class OpponentRatingsClipboardParserTest(unittest.TestCase):
    def test_exact_spanish_fixture_parses_metadata_and_nine_ratings(self):
        result = parse_opponent_ratings_clipboard(SPANISH_FIXTURE)

        self.assertTrue(result.success)
        self.assertEqual(result.team_name, "pata2008")
        self.assertEqual(result.team_id, "109910")
        self.assertEqual(result.match_id, "764960153")
        self.assertEqual(result.source_language, "es")
        self.assertEqual(
            result.ratings,
            {
                "midfield": 5.25,
                "right_defense": 6.75,
                "central_defense": 7.00,
                "left_defense": 5.50,
                "right_attack": 5.25,
                "central_attack": 4.50,
                "left_attack": 4.00,
                "indirect_defense": 7.00,
                "indirect_attack": 6.50,
            },
        )

    def test_average_rows_are_ignored(self):
        result = parse_opponent_ratings_clipboard(SPANISH_FIXTURE)

        self.assertEqual(result.ratings["midfield"], 5.25)
        self.assertNotIn(9.99, result.ratings.values())
        self.assertNotIn(8.88, result.ratings.values())

    def test_single_line_decimal_point_and_english_aliases_parse(self):
        text = (
            "[table][tr][th][matchid=1][/th][th colspan=2]Rival [teamid=2][/th][/tr]"
            "[tr][th]Midfield[/th][td]weak[/td][td]5.25[/td][/tr]"
            "[tr][th]Right Defense[/th][td]weak[/td][td]6.75[/td][/tr]"
            "[tr][th]Central Defense[/th][td]weak[/td][td]7.00[/td][/tr]"
            "[tr][th]Left Defense[/th][td]weak[/td][td]5.50[/td][/tr]"
            "[tr][th]Right Attack[/th][td]weak[/td][td]5.25[/td][/tr]"
            "[tr][th]Central Attack[/th][td]weak[/td][td]4.50[/td][/tr]"
            "[tr][th]Left Attack[/th][td]weak[/td][td]4.00[/td][/tr]"
            "[tr][th colspan=3]Indirect set pieces[/th][/tr]"
            "[tr][th]Defense[/th][td]weak[/td][td]7.00[/td][/tr]"
            "[tr][th]Attack[/th][td]weak[/td][td]6.50[/td][/tr][/table]"
        )

        result = parse_opponent_ratings_clipboard(text)

        self.assertTrue(result.success)
        self.assertEqual(result.source_language, "en")
        self.assertEqual(result.ratings["indirect_defense"], 7.0)
        self.assertEqual(result.ratings["indirect_attack"], 6.5)

    def test_partial_import_warns_and_preserves_available_values(self):
        result = parse_opponent_ratings_clipboard(
            "[tr][th]Mediocampo[/th][td][/td][td]5,25[/td][/tr]"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.ratings, {"midfield": 5.25})
        self.assertIn("missing:right_defense", result.warnings)
        self.assertIn("missing_optional:indirect_defense", result.warnings)

    def test_invalid_clipboard_and_too_large_input_fail_cleanly(self):
        self.assertFalse(parse_opponent_ratings_clipboard("").success)
        unrelated = parse_opponent_ratings_clipboard("hello world")
        self.assertFalse(unrelated.success)
        self.assertEqual(
            unrelated.error_key,
            "opponents.clipboard.error.no_ratings",
        )
        too_large = parse_opponent_ratings_clipboard("x" * (MAX_CLIPBOARD_LENGTH + 1))
        self.assertFalse(too_large.success)
        self.assertEqual(too_large.error_key, "opponents.clipboard.error.too_large")

    def test_duplicate_equal_value_is_accepted_conflict_warns(self):
        equal = parse_opponent_ratings_clipboard(
            "[tr][th]Mediocampo[/th][td][/td][td]5,25[/td][/tr]"
            "[tr][th]Mediocampo[/th][td][/td][td]5.25[/td][/tr]"
        )
        conflict = parse_opponent_ratings_clipboard(
            "[tr][th]Mediocampo[/th][td][/td][td]5,25[/td][/tr]"
            "[tr][th]Mediocampo[/th][td][/td][td]6.25[/td][/tr]"
        )

        self.assertEqual(equal.ratings["midfield"], 5.25)
        self.assertIn("conflicting_duplicate:midfield", conflict.warnings)

    def test_malformed_numeric_warns_without_success_when_no_values(self):
        result = parse_opponent_ratings_clipboard(
            "[tr][th]Mediocampo[/th][td][/td][td]5,2,5[/td][/tr]"
        )

        self.assertFalse(result.success)
        self.assertIn("invalid_numeric:midfield", result.warnings)


class OpponentRatingsUITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        configure_localization("en")
        self.page = OpponentsPage()

    def tearDown(self):
        configure_localization("en")

    def test_canonical_field_order_and_cross_sector_mapping_are_unchanged(self):
        self.assertEqual(
            HATTRICK_SECTOR_ORDER,
            (
                "midfield",
                "right_defense",
                "central_defense",
                "left_defense",
                "right_attack",
                "central_attack",
                "left_attack",
                "indirect_defense",
                "indirect_attack",
            ),
        )
        self.assertEqual(ALL_RATING_FIELDS, HATTRICK_SECTOR_ORDER)
        self.assertIn(
            ("our_left_attack", "left_attack", "right_defense"),
            MATCHUP_PAIRS,
        )
        self.assertIn(
            ("our_right_attack", "right_attack", "left_defense"),
            MATCHUP_PAIRS,
        )

    def test_opponent_editor_uses_hattrick_order_and_localized_spanish_labels(self):
        configure_localization("es")
        page = OpponentsPage()

        self.assertEqual(page.ratings_grid.rating_order(), HATTRICK_SECTOR_ORDER)
        self.assertEqual(
            list(page.ratings_grid.rating_labels().values()),
            [
                "Mediocampo",
                "Defensa derecha",
                "Defensa central",
                "Defensa izquierda",
                "Ataque derecho",
                "Ataque central",
                "Ataque izquierdo",
                "Defensa de tiro indirecto",
                "Ataque de tiro indirecto",
            ],
        )

    def test_paste_button_exists_and_is_accessible(self):
        self.assertEqual(self.page.paste_ratings_button.text(), "Paste Ratings")
        self.assertEqual(
            self.page.paste_ratings_button.accessibleName(),
            "Paste Ratings",
        )
        self.assertTrue(self.page.paste_ratings_button.toolTip())

    def test_cancelled_preview_leaves_form_unchanged(self):
        QApplication.clipboard().setText(SPANISH_FIXTURE)
        self.page.name_input.setText("Existing")
        before = self.page.ratings_grid.ratings()
        self.page._show_clipboard_preview = lambda _result: False

        self.page._paste_ratings_from_clipboard()

        self.assertEqual(self.page.name_input.text(), "Existing")
        self.assertEqual(self.page.ratings_grid.ratings(), before)

    def test_apply_updates_parsed_fields_and_keeps_existing_name_on_difference(self):
        QApplication.clipboard().setText(SPANISH_FIXTURE)
        self.page.name_input.setText("Existing")
        self.page._show_clipboard_preview = lambda _result: True

        self.page._paste_ratings_from_clipboard()

        ratings = self.page.ratings_grid.ratings()
        self.assertEqual(self.page.name_input.text(), "Existing")
        self.assertEqual(ratings["midfield"], 5.25)
        self.assertEqual(ratings["indirect_attack"], 6.50)
        self.assertIn("Existing name was kept", self.page.message_label.text())

    def test_partial_apply_preserves_unparsed_existing_fields(self):
        QApplication.clipboard().setText(
            "[tr][th]Mediocampo[/th][td][/td][td]5,25[/td][/tr]"
        )
        self.page.ratings_grid.update_rating_values({"right_defense": 99.0})
        self.page._show_clipboard_preview = lambda _result: True

        self.page._paste_ratings_from_clipboard()

        ratings = self.page.ratings_grid.ratings()
        self.assertEqual(ratings["midfield"], 5.25)
        self.assertEqual(ratings["right_defense"], 99.0)

    def test_invalid_clipboard_preserves_form(self):
        QApplication.clipboard().setText("not a rating table")
        before = self.page.ratings_grid.ratings()

        self.page._paste_ratings_from_clipboard()

        self.assertEqual(self.page.ratings_grid.ratings(), before)
        self.assertIn("No Hattrick ratings", self.page.message_label.text())


class DecimalSpinBoxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        configure_localization("en")
        self.spin = DecimalSpinBox()
        self.spin.setRange(0, 1000)
        self.spin.setDecimals(2)
        self.spin.setSingleStep(0.5)

    def tearDown(self):
        configure_localization("en")

    def test_accepts_comma_and_point_in_any_ui_language(self):
        self.assertEqual(self.spin.valueFromText("5.25"), 5.25)
        self.assertEqual(self.spin.valueFromText("5,25"), 5.25)

        configure_localization("es")
        self.assertEqual(self.spin.valueFromText("5.25"), 5.25)
        self.assertEqual(self.spin.valueFromText("5,25"), 5.25)

    def test_display_normalizes_to_active_language(self):
        self.assertEqual(self.spin.textFromValue(5.25), "5.25")
        configure_localization("es")
        self.assertEqual(self.spin.textFromValue(5.25), "5,25")

    def test_validation_rejects_double_separator_and_letters(self):
        state, _, _ = self.spin.validate("5,2,5", 0)
        self.assertEqual(state, QValidator.Invalid)
        state, _, _ = self.spin.validate("abc", 0)
        self.assertEqual(state, QValidator.Invalid)
        state, _, _ = self.spin.validate("5,25", 0)
        self.assertEqual(state, QValidator.Acceptable)

    def test_minimum_maximum_and_arrow_increment(self):
        self.assertEqual(self.spin.valueFromText("0"), 0.0)
        self.assertEqual(self.spin.valueFromText("1000"), 1000.0)
        self.spin.setValue(5.25)
        self.spin.stepBy(1)
        self.assertEqual(self.spin.value(), 5.75)


if __name__ == "__main__":
    unittest.main()
