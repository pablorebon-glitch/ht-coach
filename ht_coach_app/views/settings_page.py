from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage


class SettingsPage(BasePage):
    language_changed = Signal(str)
    advisor_verbosity_changed = Signal(str)
    season_calendar_save_requested = Signal(object, str, int)
    season_calendar_recalculate_requested = Signal()
    data_import_requested = Signal(str)

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

        self._build_season_calendar_section()
        self._build_portable_data_section()

    def _build_portable_data_section(self):
        card = QFrame()
        card.setObjectName("workspacePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel(t("settings.portable_data.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        explanation = QLabel(t("settings.portable_data.explanation"))
        explanation.setWordWrap(True)
        explanation.setObjectName("pageSubtitle")
        layout.addWidget(explanation)

        self.data_import_status_label = QLabel("")
        self.data_import_status_label.setWordWrap(True)
        layout.addWidget(self.data_import_status_label)

        button_row = QHBoxLayout()
        self.data_import_button = QPushButton(t("settings.portable_data.import_action"))
        self.data_import_button.clicked.connect(self._select_data_import_directory)
        button_row.addWidget(self.data_import_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.body_layout.addWidget(card)

    def _select_data_import_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            t("settings.portable_data.select_title"),
        )
        if directory:
            self.data_import_requested.emit(directory)

    def confirm_data_import(self, source, destination, files, backup):
        box = QMessageBox(self)
        box.setWindowTitle(t("settings.portable_data.confirm_title"))
        file_list = "\n".join(f"- {item}" for item in files)
        box.setText(
            t(
                "settings.portable_data.confirm_message",
                source=source,
                destination=destination,
                files=file_list,
                backup=backup,
            )
        )
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        box.setDefaultButton(QMessageBox.Cancel)
        return box.exec() == QMessageBox.Ok

    def set_data_import_status(self, message):
        self.data_import_status_label.setText(message or "")

    def _build_season_calendar_section(self):
        """Alpha 0.6.7 HF-02, Part 13: Configuración -> Calendario de
        temporada HT. Deliberately a distinct card, never merged into
        the training-cycle concept -- see the explanation label."""
        card = QFrame()
        card.setObjectName("workspacePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel(t("settings.season_calendar.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        explanation = QLabel(t("settings.season_calendar.explanation"))
        explanation.setWordWrap(True)
        explanation.setObjectName("pageSubtitle")
        layout.addWidget(explanation)

        form = QFormLayout()
        form.setSpacing(10)

        self.season_number_spin = QSpinBox()
        self.season_number_spin.setRange(1, 999)
        form.addRow(t("settings.season_calendar.season_number"), self.season_number_spin)

        self.season_start_date_edit = self._build_date_edit()
        form.addRow(t("settings.season_calendar.start_date"), self.season_start_date_edit)

        self.season_total_weeks_spin = QSpinBox()
        self.season_total_weeks_spin.setRange(1, 52)
        self.season_total_weeks_spin.setValue(16)
        form.addRow(t("settings.season_calendar.total_weeks"), self.season_total_weeks_spin)

        self.season_timezone_combo = QComboBox()
        self.season_timezone_combo.addItem(
            "America/Argentina/Buenos_Aires", "America/Argentina/Buenos_Aires"
        )
        self.season_timezone_combo.addItem("America/Buenos_Aires", "America/Buenos_Aires")
        self.season_timezone_combo.addItem("UTC", "UTC")
        form.addRow(t("settings.season_calendar.timezone"), self.season_timezone_combo)

        layout.addLayout(form)

        self.season_calendar_status_label = QLabel("")
        self.season_calendar_status_label.setWordWrap(True)
        layout.addWidget(self.season_calendar_status_label)

        button_row = QHBoxLayout()
        self.season_calendar_save_button = QPushButton(t("settings.season_calendar.save"))
        self.season_calendar_save_button.clicked.connect(self._emit_season_calendar_save)
        self.season_calendar_cancel_button = QPushButton(t("settings.season_calendar.cancel"))
        self.season_calendar_cancel_button.clicked.connect(self._reload_season_calendar_form)
        self.season_calendar_recalculate_button = QPushButton(
            t("settings.season_calendar.recalculate")
        )
        self.season_calendar_recalculate_button.clicked.connect(
            self.season_calendar_recalculate_requested
        )
        button_row.addWidget(self.season_calendar_save_button)
        button_row.addWidget(self.season_calendar_cancel_button)
        button_row.addWidget(self.season_calendar_recalculate_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.body_layout.addWidget(card)
        self._season_calendar_card = card

    @staticmethod
    def _build_date_edit():
        from PySide6.QtCore import QDate
        from PySide6.QtWidgets import QDateEdit

        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        edit.setDate(QDate.currentDate())
        return edit

    def set_season_calendar_config(self, config):
        """Populates the form from a `SeasonCalendarConfig` -- also
        used by "Cancelar" to discard unsaved edits."""
        from PySide6.QtCore import QDate

        self._loaded_season_calendar_config = config
        if config.season_number is not None:
            self.season_number_spin.setValue(config.season_number)
        if config.season_start_date:
            qdate = QDate.fromString(config.season_start_date[:10], "yyyy-MM-dd")
            if qdate.isValid():
                self.season_start_date_edit.setDate(qdate)
        self.season_total_weeks_spin.setValue(config.total_weeks or 16)
        index = self.season_timezone_combo.findData(config.timezone)
        if index >= 0:
            self.season_timezone_combo.setCurrentIndex(index)

    def _reload_season_calendar_form(self):
        config = getattr(self, "_loaded_season_calendar_config", None)
        if config is not None:
            self.set_season_calendar_config(config)

    def _emit_season_calendar_save(self):
        self.season_calendar_save_requested.emit(
            self.season_number_spin.value(),
            self.season_start_date_edit.date().toString("yyyy-MM-dd"),
            self.season_total_weeks_spin.value(),
        )

    def set_season_calendar_status(self, message):
        self.season_calendar_status_label.setText(message or "")

    def confirm_recalculation(self, updated_count):
        """Part 13: show how many records will be updated before
        applying."""
        return QMessageBox.question(
            self,
            t("settings.season_calendar.recalculate"),
            t("settings.season_calendar.recalculate_confirm", count=updated_count),
        ) == QMessageBox.Yes

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
