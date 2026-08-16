"""Alpha 0.6.7 HF-03, Part 14: the user-facing crash message.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from ht_coach_app.core.localization import t


class CrashDialog(QDialog):
    def __init__(self, log_path, parent=None):
        super().__init__(parent)
        self._log_path = str(log_path)
        self.setWindowTitle(t("crash.title"))
        layout = QVBoxLayout(self)

        message = QLabel(t("crash.message"))
        message.setWordWrap(True)
        layout.addWidget(message)

        saved_label = QLabel(t("crash.log_saved"))
        saved_label.setWordWrap(True)
        layout.addWidget(saved_label)

        path_label = QLabel(self._log_path)
        path_label.setObjectName("crashLogPath")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        buttons = QDialogButtonBox()
        copy_button = buttons.addButton(t("crash.copy_path"), QDialogButtonBox.ActionRole)
        copy_button.clicked.connect(self._copy_path)
        close_button = buttons.addButton(t("crash.close"), QDialogButtonBox.AcceptRole)
        close_button.clicked.connect(self.accept)
        layout.addWidget(buttons)

    def _copy_path(self):
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._log_path)


def show_crash_dialog(log_path, parent=None):
    try:
        dialog = CrashDialog(log_path, parent)
        dialog.exec()
    except Exception:
        pass
