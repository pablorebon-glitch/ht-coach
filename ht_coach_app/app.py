import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ht_coach_app.core.constants import APP_NAME
from ht_coach_app.views.main_window import MainWindow


def create_application(argv=None):
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("HT Coach")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(_application_stylesheet())
    return app


def run(argv=None):
    app = create_application(argv)
    window = MainWindow()
    window.show()
    return app.exec()


def _application_stylesheet():
    return """
        QMainWindow {
            background: #f5f6f8;
        }

        QToolBar {
            background: #ffffff;
            border-bottom: 1px solid #d8dde6;
            spacing: 8px;
            padding: 6px;
        }

        QStatusBar {
            background: #ffffff;
            border-top: 1px solid #d8dde6;
            color: #384252;
        }

        QLabel#pageTitle {
            color: #1f2937;
            font-size: 22px;
            font-weight: 650;
        }

        QLabel#pageSubtitle {
            color: #667085;
            font-size: 12px;
        }

        QLabel#sectionTitle {
            color: #1f2937;
            font-size: 14px;
            font-weight: 650;
        }

        QLabel[state="error"] {
            color: #b42318;
        }

        QLabel[state="ok"] {
            color: #027a48;
        }

        QFrame#workspacePanel,
        QFrame#resultCard,
        QFrame#metadataPanel,
        QFrame#statePanel {
            background: #ffffff;
            border: 1px solid #e4e7ec;
            border-radius: 8px;
        }

        QFrame#recommendedCard {
            background: #eef6ff;
            border: 2px solid #2563eb;
            border-radius: 8px;
        }

        QLabel#recommendedBadge {
            background: #2563eb;
            border-radius: 6px;
            color: #ffffff;
            font-size: 11px;
            font-weight: 650;
            padding: 4px 8px;
        }

        QLabel#resultHeadline {
            color: #1f2937;
            font-size: 18px;
            font-weight: 650;
        }

        QFrame#metricTile {
            background: #ffffff;
            border: 1px solid #d8dde6;
            border-radius: 6px;
        }

        QLabel#metricLabel {
            color: #667085;
            font-size: 11px;
        }

        QLabel#metricValue {
            color: #111827;
            font-size: 16px;
            font-weight: 650;
        }

        QLabel#metadataValue {
            color: #111827;
            font-weight: 650;
        }

        QPushButton#primaryAction {
            background: #2563eb;
            border: 1px solid #2563eb;
            border-radius: 6px;
            color: #ffffff;
            font-weight: 650;
            padding: 8px 14px;
        }

        QPushButton#primaryAction:disabled {
            background: #98a2b3;
            border-color: #98a2b3;
        }

        QFrame#pageHeader {
            background: #ffffff;
            border-bottom: 1px solid #e4e7ec;
        }

        QListWidget#navigationList {
            background: #111827;
            border: 0;
            color: #d1d5db;
            font-size: 13px;
            outline: 0;
        }

        QListWidget#navigationList::item {
            border-radius: 6px;
            margin: 3px 8px;
            padding: 10px 12px;
        }

        QListWidget#navigationList::item:selected {
            background: #2563eb;
            color: #ffffff;
        }

        QListWidget#navigationList::item:hover:!selected {
            background: #1f2937;
            color: #ffffff;
        }
    """
