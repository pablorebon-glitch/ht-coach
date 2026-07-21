from datetime import date, timedelta
from zoneinfo import ZoneInfo

from engine.weekly_training.models import PLAYMAKING, TrainingWeek, TrainingWeekStatus


def active_training_week(today=None, timezone_name="America/Buenos_Aires", training_type=PLAYMAKING):
    if today is None:
        today = date.today()
    if hasattr(today, "astimezone"):
        today = today.astimezone(ZoneInfo(timezone_name)).date()

    weekday = today.weekday()
    days_since_sunday = (weekday + 1) % 7
    start = today - timedelta(days=days_since_sunday)
    training_update = start + timedelta(days=4)
    if today >= training_update:
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
    if today is None:
        today = date.today()
    if hasattr(today, "astimezone"):
        today = today.astimezone(ZoneInfo(timezone_name)).date()
    if today < current_week.training_update_date:
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
