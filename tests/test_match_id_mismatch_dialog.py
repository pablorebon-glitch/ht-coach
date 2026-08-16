import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QTimer = pytest.importorskip("PySide6.QtCore").QTimer
QApplication = QtWidgets.QApplication
QDialog = QtWidgets.QDialog

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


def test_match_id_mismatch_dialog_apply_accepts_dialog():
    dialog = MatchIdMismatchDialog("111", "222")
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog.post_match_id_edit.setText("111")
    dialog.apply_button.click()

    assert accepted == [True]
    assert dialog.result() == QDialog.Accepted


def test_match_id_mismatch_dialog_duplicate_apply_does_not_accept_twice():
    dialog = MatchIdMismatchDialog("111", "222")
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))

    dialog.post_match_id_edit.setText("111")
    dialog.apply_button.click()
    dialog.apply_button.click()

    assert accepted == [True]


def test_request_match_id_returns_corrected_id_after_apply(monkeypatch):
    created = []
    original_init = MatchIdMismatchDialog.__init__

    def capture_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        created.append(self)

    monkeypatch.setattr(MatchIdMismatchDialog, "__init__", capture_init)

    def click_apply():
        dialog = created[0]
        dialog.post_match_id_edit.setText("111")
        dialog.apply_button.click()

    QTimer.singleShot(0, click_apply)

    assert MatchIdMismatchDialog.request_match_id("111", "222") == "111"
