from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ht_coach_app.core.localization import t


class MatchIdMismatchDialog(QDialog):
    def __init__(self, pre_match_id, post_match_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("match.official_import.match_id_mismatch.title"))
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        message = QLabel(t("match.official_import.match_id_mismatch.message"))
        message.setWordWrap(True)
        layout.addWidget(message)

        warning = QLabel(t("match.official_import.match_id_mismatch.warning"))
        warning.setWordWrap(True)
        warning.setObjectName("warningText")
        layout.addWidget(warning)

        form = QFormLayout()
        self.pre_match_id_edit = QLineEdit(str(pre_match_id or ""))
        self.post_match_id_edit = QLineEdit(str(post_match_id or ""))
        form.addRow(
            t("match.official_import.match_id_mismatch.pre_match_id"),
            self.pre_match_id_edit,
        )
        form.addRow(
            t("match.official_import.match_id_mismatch.post_match_id"),
            self.post_match_id_edit,
        )
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        self.apply_button = self.buttons.button(QDialogButtonBox.Apply)
        self.back_button = self.buttons.button(QDialogButtonBox.Cancel)
        self.apply_button.setText(t("common.apply"))
        self.back_button.setText(t("common.back"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.pre_match_id_edit.textChanged.connect(self._update_apply_state)
        self.post_match_id_edit.textChanged.connect(self._update_apply_state)
        self._update_apply_state()

    def _update_apply_state(self):
        self.apply_button.setEnabled(
            bool(self.match_id()) and self.pre_match_id_edit.text().strip()
            == self.post_match_id_edit.text().strip()
        )

    def match_id(self):
        pre_id = self.pre_match_id_edit.text().strip()
        post_id = self.post_match_id_edit.text().strip()
        return pre_id if pre_id and pre_id == post_id else ""

    @staticmethod
    def request_match_id(pre_match_id, post_match_id, parent=None):
        dialog = MatchIdMismatchDialog(pre_match_id, post_match_id, parent)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.match_id() or None
