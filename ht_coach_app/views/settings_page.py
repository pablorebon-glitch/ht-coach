from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
)

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage


class SettingsPage(BasePage):
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            t("settings.title"),
            t("settings.subtitle"),
            parent
        )
        self._build()

    def _build(self):
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)

        self.language_combo = QComboBox()
        self.language_combo.addItem(t("settings.english"), "en")
        self.language_combo.addItem(t("settings.spanish"), "es")
        self.language_combo.currentIndexChanged.connect(
            self._emit_language_changed
        )

        self.language_help_label = QLabel(t("settings.language_help"))
        self.language_help_label.setWordWrap(True)
        self.language_help_label.setObjectName("pageSubtitle")

        self.language_label = QLabel(t("settings.language"))
        form.addRow(self.language_label, self.language_combo)
        self.body_layout.addLayout(form)
        self.body_layout.addWidget(self.language_help_label)

    def set_language(self, language):
        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    def retranslate_ui(self):
        current_language = self.language_combo.currentData()
        self.set_page_text(
            t("settings.title"),
            t("settings.subtitle"),
        )
        self.language_combo.blockSignals(True)
        self.language_combo.setItemText(0, t("settings.english"))
        self.language_combo.setItemText(1, t("settings.spanish"))
        index = self.language_combo.findData(current_language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)
        self.language_label.setText(t("settings.language"))
        self.language_help_label.setText(t("settings.language_help"))

    def _emit_language_changed(self):
        self.language_changed.emit(
            self.language_combo.currentData() or "en"
        )
