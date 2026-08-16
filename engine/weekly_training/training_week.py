from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from engine.calendar import DEFAULT_SCHEDULE, HTCalendarService
from engine.weekly_training.models import PLAYMAKING, TrainingWeek, TrainingWeekStatus

_calendar_service = HTCalendarService(schedule=DEFAULT_SCHEDULE)


def _training_update_has_occurred(today, training_update_date):
    """Whether the Thursday training update for `training_update_date`
    has already processed, as of `today`.

    HF: the previous version of this function only ever compared bare
    `date` objects (`today >= training_update_date`), which silently
    discarded whatever hour was actually passed in -- any moment on
    Thursday counted as "already processed", even 00:01. This module
    now asks `HTCalendarService` for the precise Thursday-21:00 (or
    whatever the schedule says) cutoff *whenever a full `datetime` with
    real time-of-day information is available* -- `today=None` (the
    common case, meaning "right now") always gets full precision via
    `datetime.now()`. A caller that explicitly passes a bare `date`
    (no time component) keeps the original date-only comparison, for
    backward compatibility with existing callers/tests that don't care
    about the exact hour.
    """
    if isinstance(today, datetime):
        naive_today = today.replace(tzinfo=None)
        return _calendar_service.is_training_processed(naive_today) if (
            naive_today.date() == training_update_date
        ) else naive_today.date() >= training_update_date
    return today >= training_update_date


def active_training_week(today=None, timezone_name="America/Buenos_Aires", training_type=PLAYMAKING):
    now = None
    if today is None:
        now = datetime.now(ZoneInfo(timezone_name))
        today = now.date()
    elif hasattr(today, "astimezone"):
        now = today.astimezone(ZoneInfo(timezone_name))
        today = now.date()

    weekday = today.weekday()
    days_since_sunday = (weekday + 1) % 7
    start = today - timedelta(days=days_since_sunday)
    training_update = start + timedelta(days=4)
    rolled_over = (
        _training_update_has_occurred(now, training_update)
        if now is not None
        else _training_update_has_occurred(today, training_update)
    )
    if rolled_over:
        start = start + timedelta(days=7)
        training_update = start + timedelta(days=4)

    end = training_update - timedelta(days=1)
    return TrainingWeek(
        week_id=f"{start.isoformat()}:{training_type}",
        start_date=start,
        end_date=end,
        training_update_date=training_update,
        first_match_date=start,
        second_match_date=start + timedelta(days=3),
        active_training_type=training_type,
        status=TrainingWeekStatus.PLANNING,
    )


def rollover_week(current_week, today=None, timezone_name="America/Buenos_Aires"):
    if current_week is None:
        return None, active_training_week(today, timezone_name)
    now = None
    if today is None:
        now = datetime.now(ZoneInfo(timezone_name))
        today = now.date()
    elif hasattr(today, "astimezone"):
        now = today.astimezone(ZoneInfo(timezone_name))
        today = now.date()

    rolled_over = (
        _training_update_has_occurred(now, current_week.training_update_date)
        if now is not None
        else _training_update_has_occurred(today, current_week.training_update_date)
    )
    if not rolled_over:
        return None, current_week
    archived = TrainingWeek(
        week_id=current_week.week_id,
        start_date=current_week.start_date,
        end_date=current_week.end_date,
        training_update_date=current_week.training_update_date,
        first_match_date=current_week.first_match_date,
        second_match_date=current_week.second_match_date,
        active_training_type=current_week.active_training_type,
        status=TrainingWeekStatus.ARCHIVED,
    )
    return archived, active_training_week(
        today,
        timezone_name,
        current_week.active_training_type,
    )
