from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
)

from ht_coach_app.core.localization import t


class MatchIntelligenceImportDialog(QDialog):
    """Same one-step paste-and-confirm flow as Match's own import
    dialog, plus an explicit PRE/POST choice -- Match Intelligence is
    where the full official-rating lifecycle (both captures) lives."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("official_match_intelligence.import.title"))
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        instructions = QLabel(t("official_match_intelligence.import.instructions"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        slot_row = QHBoxLayout()
        self.pre_radio = QRadioButton(t("official_match_intelligence.import.slot_pre"))
        self.post_radio = QRadioButton(t("official_match_intelligence.import.slot_post"))
        self.pre_radio.setChecked(True)
        self.slot_group = QButtonGroup(self)
        self.slot_group.addButton(self.pre_radio)
        self.slot_group.addButton(self.post_radio)
        slot_row.addWidget(self.pre_radio)
        slot_row.addWidget(self.post_radio)
        layout.addLayout(slot_row)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(t("match.official_import.placeholder"))
        self.text_edit.setAcceptRichText(False)
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(t("match.official_import.confirm"))
        buttons.button(QDialogButtonBox.Cancel).setText(t("match.official_import.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def slot(self):
        return "post" if self.post_radio.isChecked() else "pre"

    def pasted_text(self):
        return self.text_edit.toPlainText()

    @staticmethod
    def request_import(parent=None):
        """Opens the dialog modally; returns (text, slot) or None if
        the user cancelled or left the text empty."""
        dialog = MatchIntelligenceImportDialog(parent)
        if dialog.exec() != QDialog.Accepted:
            return None
        text = dialog.pasted_text().strip()
        if not text:
            return None
        return text, dialog.slot()
