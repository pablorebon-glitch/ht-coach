from datetime import datetime

from engine.calendar import (
    DEFAULT_SCHEDULE,
    HTCalendarService,
    HTWeekday,
    HTWeekState,
)


def _service():
    return HTCalendarService()


def test_sunday_before_match_is_pre_league_match():
    service = _service()
    assert service.current_state(datetime(2026, 8, 2, 10, 0)) == HTWeekState.PRE_LEAGUE_MATCH


def test_sunday_after_match_is_post_league_match():
    service = _service()
    assert service.current_state(datetime(2026, 8, 2, 20, 0)) == HTWeekState.POST_LEAGUE_MATCH


def test_monday_is_post_league_match():
    service = _service()
    assert service.current_state(datetime(2026, 8, 3, 10, 0)) == HTWeekState.POST_LEAGUE_MATCH


def test_tuesday_is_pre_friendly():
    service = _service()
    assert service.current_state(datetime(2026, 8, 4, 10, 0)) == HTWeekState.PRE_FRIENDLY


def test_wednesday_before_friendly_is_pre_friendly():
    service = _service()
    assert service.current_state(datetime(2026, 8, 5, 10, 0)) == HTWeekState.PRE_FRIENDLY


def test_wednesday_after_friendly_is_post_friendly():
    service = _service()
    assert service.current_state(datetime(2026, 8, 5, 21, 0)) == HTWeekState.POST_FRIENDLY


def test_thursday_before_training_is_pre_training():
    service = _service()
    assert service.current_state(datetime(2026, 8, 6, 10, 0)) == HTWeekState.PRE_TRAINING


def test_thursday_after_training_is_post_training():
    service = _service()
    assert service.current_state(datetime(2026, 8, 6, 22, 0)) == HTWeekState.POST_TRAINING


def test_thursday_exactly_at_training_hour_is_post_training():
    service = _service()
    assert service.current_state(datetime(2026, 8, 6, 21, 0)) == HTWeekState.POST_TRAINING


def test_friday_is_post_financial_update():
    service = _service()
    assert service.current_state(datetime(2026, 8, 7, 6, 0)) == HTWeekState.POST_FINANCIAL_UPDATE
    assert service.current_state(datetime(2026, 8, 7, 23, 0)) == HTWeekState.POST_FINANCIAL_UPDATE


def test_saturday_is_pre_youth_scout():
    service = _service()
    assert service.current_state(datetime(2026, 8, 8, 0, 0)) == HTWeekState.PRE_YOUTH_SCOUT
    assert service.current_state(datetime(2026, 8, 8, 23, 0)) == HTWeekState.PRE_YOUTH_SCOUT


def test_all_eight_states_are_reachable_across_a_full_week():
    service = _service()
    hours = [
        datetime(2026, 8, 2, 10, 0), datetime(2026, 8, 2, 20, 0),
        datetime(2026, 8, 3, 10, 0), datetime(2026, 8, 4, 10, 0),
        datetime(2026, 8, 5, 10, 0), datetime(2026, 8, 5, 21, 0),
        datetime(2026, 8, 6, 10, 0), datetime(2026, 8, 6, 22, 0),
        datetime(2026, 8, 7, 12, 0), datetime(2026, 8, 8, 12, 0),
    ]
    observed = {service.current_state(h) for h in hours}
    assert observed == set(HTWeekState)


def test_training_week_id_does_not_change_on_monday():
    service = _service()
    sunday_id = service.training_week_id(datetime(2026, 8, 2, 20, 0))
    monday_id = service.training_week_id(datetime(2026, 8, 3, 10, 0))
    assert sunday_id == monday_id


def test_training_week_id_stays_stable_through_wednesday():
    service = _service()
    monday_id = service.training_week_id(datetime(2026, 8, 3, 10, 0))
    wednesday_id = service.training_week_id(datetime(2026, 8, 5, 23, 59))
    assert monday_id == wednesday_id


def test_training_week_id_changes_exactly_at_thursday_processing_hour():
    service = _service()
    before = service.training_week_id(datetime(2026, 8, 6, 20, 59))
    after = service.training_week_id(datetime(2026, 8, 6, 21, 0))
    assert before != after


def test_training_processed_false_before_thursday_cutoff():
    service = _service()
    assert service.is_training_processed(datetime(2026, 8, 6, 20, 59)) is False


def test_training_processed_true_after_thursday_cutoff():
    service = _service()
    assert service.is_training_processed(datetime(2026, 8, 6, 21, 0)) is True


def test_training_week_id_is_stable_across_the_whole_active_cycle():
    service = _service()
    ids = {
        service.training_week_id(datetime(2026, 8, 2, 20, 0)),
        service.training_week_id(datetime(2026, 8, 3, 8, 0)),
        service.training_week_id(datetime(2026, 8, 4, 8, 0)),
        service.training_week_id(datetime(2026, 8, 5, 8, 0)),
        service.training_week_id(datetime(2026, 8, 6, 20, 59)),
    }
    assert len(ids) == 1


def test_days_until_training_counts_down_to_zero_on_thursday():
    service = _service()
    assert service.days_until_training(datetime(2026, 8, 2, 10, 0)) == 4
    assert service.days_until_training(datetime(2026, 8, 5, 10, 0)) == 1
    assert service.days_until_training(datetime(2026, 8, 6, 10, 0)) == 0


def test_days_until_training_wraps_to_next_week_after_processing():
    service = _service()
    assert service.days_until_training(datetime(2026, 8, 6, 22, 0)) == 7


def test_days_until_finances_counts_down_to_friday():
    service = _service()
    assert service.days_until_finances(datetime(2026, 8, 2, 10, 0)) == 5
    assert service.days_until_finances(datetime(2026, 8, 7, 7, 0)) == 0  # before the 08:00 update


def test_days_until_finances_wraps_after_update_processed():
    service = _service()
    assert service.days_until_finances(datetime(2026, 8, 7, 10, 0)) == 7


def test_days_until_match_counts_down_to_sunday():
    service = _service()
    assert service.days_until_match(datetime(2026, 8, 3, 10, 0)) == 6
    assert service.days_until_match(datetime(2026, 8, 8, 10, 0)) == 1


def test_days_until_match_is_zero_on_match_day_before_kickoff():
    service = _service()
    assert service.days_until_match(datetime(2026, 8, 2, 10, 0)) == 0


def test_next_transition_from_monday_is_friendly():
    service = _service()
    state, when = service.next_transition(datetime(2026, 8, 3, 10, 0))
    assert state == HTWeekState.POST_FRIENDLY
    assert when.date() == datetime(2026, 8, 5).date()


def test_next_transition_from_saturday_wraps_to_next_sunday_match():
    service = _service()
    state, when = service.next_transition(datetime(2026, 8, 8, 23, 0))
    assert state == HTWeekState.POST_LEAGUE_MATCH
    assert when.date() == datetime(2026, 8, 9).date()


def test_week_snapshot_reflects_all_fields_consistently():
    service = _service()
    snapshot = service.week_snapshot(datetime(2026, 8, 3, 10, 0))
    assert snapshot.weekday == HTWeekday.MONDAY
    assert snapshot.state == HTWeekState.POST_LEAGUE_MATCH
    assert snapshot.league_match_played is True
    assert snapshot.friendly_played is False
    assert snapshot.training_processed is False


def test_week_snapshot_to_dict_roundtrips_serializable_types():
    service = _service()
    snapshot = service.week_snapshot(datetime(2026, 8, 3, 10, 0))
    payload = snapshot.to_dict()
    assert payload["weekday"] == "monday"
    assert payload["state"] == "post_league_match"
    assert isinstance(payload["training_processed"], bool)


def test_custom_schedule_changes_training_hour():
    from engine.calendar import HTWeekScheduleConfig

    custom = HTWeekScheduleConfig(training_hour=12)
    service = HTCalendarService(schedule=custom)
    assert service.is_training_processed(datetime(2026, 8, 6, 12, 0)) is True
    assert service.is_training_processed(datetime(2026, 8, 6, 11, 59)) is False


def test_default_schedule_uses_21_00_for_training():
    assert DEFAULT_SCHEDULE.training_hour == 21


def test_injectable_clock_used_when_now_omitted():
    fixed = datetime(2026, 8, 6, 22, 0)
    service = HTCalendarService(clock=lambda: fixed)
    assert service.current_state() == HTWeekState.POST_TRAINING
