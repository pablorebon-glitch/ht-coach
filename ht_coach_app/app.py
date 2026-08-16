import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from ht_coach_app.core.constants import APP_NAME
from ht_coach_app.core.paths import application_paths
from ht_coach_app.core.portable import (
    build_import_plan,
    ensure_portable_writable,
    import_data_directory,
    installed_data_dir,
    portable_data_is_empty,
)
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
    paths = application_paths()
    if paths.is_portable:
        if not ensure_portable_writable(paths):
            QMessageBox.critical(
                None,
                "HT Coach",
                "HT Coach no puede guardar datos en esta ubicacion.\n\n"
                "Copia la carpeta a una ubicacion con permisos de escritura "
                "o revisa el pendrive.",
            )
            return 1
        _offer_appdata_import(paths)

    def _on_crash(log_path, exc_type, exc_value, exc_traceback):
        show_crash_dialog(log_path)

    install_crash_handler(on_crash=_on_crash)

    window = MainWindow()
    window.show()
    return app.exec()


def _offer_appdata_import(paths):
    source = installed_data_dir()
    if not portable_data_is_empty(paths) or not source.exists():
        return
    plan = build_import_plan(source, paths=paths)
    if not plan.has_files:
        return
    files = "\n".join(f"- {item.name}" for item in plan.files)
    message = (
        "Se encontraron datos existentes de HT Coach.\n\n"
        "Queres copiarlos a esta version portable?\n\n"
        f"Origen:\n{plan.source_dir}\n\n"
        f"Destino:\n{plan.destination_dir}\n\n"
        f"Archivos:\n{files}\n\n"
        f"Backup:\n{paths.backup_dir}"
    )
    box = QMessageBox()
    box.setWindowTitle("Importar datos existentes")
    box.setText(message)
    no_button = box.addButton("No copiar", QMessageBox.RejectRole)
    copy_button = box.addButton("Copiar datos", QMessageBox.AcceptRole)
    box.setDefaultButton(copy_button)
    box.exec()
    if box.clickedButton() is no_button:
        return
    import_data_directory(source, reason="first_portable_launch", paths=paths)
