from datetime import datetime

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.calendar import HTCalendarService
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.services.ht_week_context_provider import (
    current_week_snapshot,
    get_calendar_service,
    set_calendar_service,
)
from ht_coach_app.services.ht_week_formatting import format_ht_week_status


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")
    set_calendar_service(HTCalendarService())


def test_provider_returns_a_shared_service_instance():
    service_a = get_calendar_service()
    service_b = get_calendar_service()
    assert service_a is service_b


def test_provider_can_be_overridden_for_tests():
    fixed = HTCalendarService(clock=lambda: datetime(2026, 8, 6, 22, 0))
    set_calendar_service(fixed)
    assert get_calendar_service() is fixed
    snapshot = current_week_snapshot()
    assert snapshot.training_processed is True


def test_format_ht_week_status_shows_all_five_milestones():
    set_calendar_service(HTCalendarService(clock=lambda: datetime(2026, 8, 3, 10, 0)))
    snapshot = current_week_snapshot()
    text = format_ht_week_status(snapshot)
    assert "Entrenamiento" in text
    assert "Amistoso" in text
    assert "Liga" in text
    assert "Actualización financiera" in text
    assert "Ojeador juvenil" in text


def test_format_ht_week_status_shows_pending_before_training_cutoff():
    set_calendar_service(HTCalendarService(clock=lambda: datetime(2026, 8, 6, 10, 0)))
    snapshot = current_week_snapshot()
    text = format_ht_week_status(snapshot)
    assert "Entrenamiento: Pendiente" in text


def test_format_ht_week_status_shows_processed_after_training_cutoff():
    set_calendar_service(HTCalendarService(clock=lambda: datetime(2026, 8, 6, 22, 0)))
    snapshot = current_week_snapshot()
    text = format_ht_week_status(snapshot)
    assert "Entrenamiento: Procesado" in text


def test_format_ht_week_status_no_raw_enum_values_leak():
    set_calendar_service(HTCalendarService(clock=lambda: datetime(2026, 8, 3, 10, 0)))
    snapshot = current_week_snapshot()
    text = format_ht_week_status(snapshot)
    assert "post_league_match" not in text
    assert "true" not in text.lower()
    assert "false" not in text.lower()


def test_format_is_compact_a_single_readable_line():
    set_calendar_service(HTCalendarService(clock=lambda: datetime(2026, 8, 3, 10, 0)))
    text = format_ht_week_status(current_week_snapshot())
    assert text.count("\n") == 0
