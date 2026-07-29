from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)

from ht_coach_app.core.localization import t


class OfficialRatingImportDialog(QDialog):
    """The whole "Import Official Match Summary" flow in one step: open,
    paste, confirm. No wizard, no extra setup pages, no metadata form --
    Match ID linking and PRE/POST classification happen automatically
    (or are confirmed afterward) once the text is parsed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("match.official_import.title"))
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        instructions = QLabel(t("match.official_import.instructions"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(t("match.official_import.placeholder"))
        self.text_edit.setAcceptRichText(False)
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText(
            t("match.official_import.confirm")
        )
        buttons.button(QDialogButtonBox.Cancel).setText(
            t("match.official_import.cancel")
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def pasted_text(self):
        return self.text_edit.toPlainText()

    @staticmethod
    def request_text(parent=None):
        """Opens the dialog modally; returns the pasted text, or None if
        the user cancelled or left it empty."""
        dialog = OfficialRatingImportDialog(parent)
        if dialog.exec() != QDialog.Accepted:
            return None
        text = dialog.pasted_text().strip()
        return text or None
