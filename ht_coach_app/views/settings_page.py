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
    advisor_verbosity_changed = Signal(str)

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

        self.advisor_verbosity_combo = QComboBox()
        self.advisor_verbosity_combo.addItem(
            t("settings.verbosity_simple"),
            "simple",
        )
        self.advisor_verbosity_combo.addItem(
            t("settings.verbosity_detailed"),
            "detailed",
        )
        self.advisor_verbosity_combo.currentIndexChanged.connect(
            self._emit_advisor_verbosity_changed
        )

        self.language_help_label = QLabel(t("settings.language_help"))
        self.language_help_label.setWordWrap(True)
        self.language_help_label.setObjectName("pageSubtitle")
        self.advisor_verbosity_help_label = QLabel(
            t("settings.advisor_verbosity_help")
        )
        self.advisor_verbosity_help_label.setWordWrap(True)
        self.advisor_verbosity_help_label.setObjectName("pageSubtitle")

        self.language_label = QLabel(t("settings.language"))
        self.advisor_verbosity_label = QLabel(
            t("settings.advisor_verbosity")
        )
        form.addRow(self.language_label, self.language_combo)
        form.addRow(
            self.advisor_verbosity_label,
            self.advisor_verbosity_combo,
        )
        self.body_layout.addLayout(form)
        self.body_layout.addWidget(self.language_help_label)
        self.body_layout.addWidget(self.advisor_verbosity_help_label)

    def set_language(self, language):
        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

    def set_advisor_verbosity(self, verbosity):
        index = self.advisor_verbosity_combo.findData(verbosity)
        if index >= 0:
            self.advisor_verbosity_combo.setCurrentIndex(index)

    def retranslate_ui(self):
        current_language = self.language_combo.currentData()
        current_verbosity = self.advisor_verbosity_combo.currentData()
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
        self.advisor_verbosity_combo.blockSignals(True)
        self.advisor_verbosity_combo.setItemText(
            0,
            t("settings.verbosity_simple"),
        )
        self.advisor_verbosity_combo.setItemText(
            1,
            t("settings.verbosity_detailed"),
        )
        index = self.advisor_verbosity_combo.findData(current_verbosity)
        if index >= 0:
            self.advisor_verbosity_combo.setCurrentIndex(index)
        self.advisor_verbosity_combo.blockSignals(False)
        self.language_label.setText(t("settings.language"))
        self.advisor_verbosity_label.setText(
            t("settings.advisor_verbosity")
        )
        self.language_help_label.setText(t("settings.language_help"))
        self.advisor_verbosity_help_label.setText(
            t("settings.advisor_verbosity_help")
        )

    def _emit_language_changed(self):
        self.language_changed.emit(
            self.language_combo.currentData() or "en"
        )

    def _emit_advisor_verbosity_changed(self):
        self.advisor_verbosity_changed.emit(
            self.advisor_verbosity_combo.currentData() or "detailed"
        )
