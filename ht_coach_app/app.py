import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ht_coach_app.core.constants import APP_NAME
from ht_coach_app.ui.design_system.styles import application_stylesheet
from ht_coach_app.views.main_window import MainWindow


def create_application(argv=None):
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("HT Coach")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(application_stylesheet())
    return app


def run(argv=None):
    app = create_application(argv)
    window = MainWindow()
    window.show()
    return app.exec()
