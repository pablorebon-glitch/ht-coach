import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ht_coach_app.core.constants import APP_NAME
from ht_coach_app.diagnostics.crash_dialog import show_crash_dialog
from ht_coach_app.diagnostics.crash_reporter import install_crash_handler
from ht_coach_app.ui.design_system.styles import application_stylesheet
from ht_coach_app.ui.input_behavior import install_page_only_wheel_policy
from ht_coach_app.views.main_window import MainWindow


def create_application(argv=None):
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("HT Coach")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(application_stylesheet())
    install_page_only_wheel_policy(app)
    return app


def run(argv=None):
    app = create_application(argv)

    def _on_crash(log_path, exc_type, exc_value, exc_traceback):
        show_crash_dialog(log_path)

    install_crash_handler(on_crash=_on_crash)

    window = MainWindow()
    window.show()
    return app.exec()
