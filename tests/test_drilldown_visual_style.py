import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.core.localization import configure_localization
from ht_coach_app.ui.design_system.styles import application_stylesheet
from ht_coach_app.widgets.drilldown_overlay import DrillDownOverlay


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def test_stylesheet_defines_white_background_for_drilldown_panel():
    css = application_stylesheet()
    assert "QFrame#drillDownPanel" in css
    idx = css.find("QFrame#drillDownPanel {")
    block = css[idx: idx + 200]
    assert "#ffffff" in block


def test_stylesheet_defines_white_background_for_detail_panel():
    css = application_stylesheet()
    assert "drillDownDetailPanel" in css


def test_stylesheet_defines_white_background_for_list_widget():
    css = application_stylesheet()
    idx = css.find("QFrame#drillDownPanel QListWidget {")
    assert idx != -1
    block = css[idx: idx + 200]
    assert "#ffffff" in block


def test_stylesheet_defines_selection_highlight():
    css = application_stylesheet()
    assert "QListWidget::item:selected" in css


def test_stylesheet_defines_close_button_style():
    css = application_stylesheet()
    assert "drillDownCloseButton" in css


def test_close_button_is_small_x_not_large_cerrar_button():
    """Requirement: close control is a small × in the top-right, no
    large 'Cerrar' button."""
    parent = __import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget()
    parent.resize(800, 600)
    overlay = DrillDownOverlay.show_over(parent, "Riesgos", [("Roberto", "Reason: x")])
    assert overlay.close_button.text() == "×"
    assert overlay.close_button.objectName() == "drillDownCloseButton"
    assert overlay.close_button.width() <= 40
    assert overlay.close_button.height() <= 40


def test_panel_has_explicit_white_palette_background():
    parent = __import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget()
    parent.resize(800, 600)
    overlay = DrillDownOverlay.show_over(parent, "Riesgos", [("Roberto", "Reason: x")])
    color = overlay.panel.palette().color(overlay.panel.backgroundRole())
    assert color.name() == "#ffffff"


def test_panel_has_a_shadow_or_border_effect():
    parent = __import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget()
    parent.resize(800, 600)
    overlay = DrillDownOverlay.show_over(parent, "Riesgos", [("Roberto", "Reason: x")])
    assert overlay.panel.graphicsEffect() is not None


def test_backdrop_is_separate_widget_from_panel():
    """The overlay must darken only the background behind the modal --
    a distinct backdrop widget, never the panel itself."""
    parent = __import__("PySide6.QtWidgets", fromlist=["QWidget"]).QWidget()
    parent.resize(800, 600)
    overlay = DrillDownOverlay.show_over(parent, "Riesgos", [("Roberto", "Reason: x")])
    assert overlay.backdrop is not overlay.panel
    assert overlay.backdrop.objectName() == "drillDownBackdrop"
