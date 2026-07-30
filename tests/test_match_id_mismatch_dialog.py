import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.widgets.match_id_mismatch_dialog import MatchIdMismatchDialog


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])


def test_match_id_mismatch_dialog_apply_enabled_only_when_ids_match():
    dialog = MatchIdMismatchDialog("111", "222")

    assert not dialog.apply_button.isEnabled()

    dialog.post_match_id_edit.setText("111")

    assert dialog.apply_button.isEnabled()
    assert dialog.match_id() == "111"


def test_match_id_mismatch_dialog_allows_editing_either_match_id():
    dialog = MatchIdMismatchDialog("111", "222")

    dialog.pre_match_id_edit.setText("222")

    assert dialog.apply_button.isEnabled()
    assert dialog.match_id() == "222"
