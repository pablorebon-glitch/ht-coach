import pytest
from datetime import date

from engine.history.enums import MatchRecordStatus
from engine.history.match_record_status import derive_match_record_status

_TODAY = date(2026, 8, 9)
_FUTURE = date(2026, 8, 16)
_PAST = date(2026, 8, 2)


def test_no_data_and_future_match_is_planned():
    status = derive_match_record_status(match_date=_FUTURE, today=_TODAY)
    assert status == MatchRecordStatus.PLANNED


def test_official_pre_and_future_match_is_pre_imported():
    status = derive_match_record_status(
        official_pre=object(), match_date=_FUTURE, today=_TODAY
    )
    assert status == MatchRecordStatus.PRE_OFFICIAL_IMPORTED


def test_official_pre_and_past_match_without_post_is_played_post_pending():
    status = derive_match_record_status(
        official_pre=object(), match_date=_PAST, today=_TODAY
    )
    assert status == MatchRecordStatus.PLAYED_POST_PENDING


def test_official_pre_and_post_is_complete():
    status = derive_match_record_status(
        official_pre=object(), official_post=object(), match_date=_PAST, today=_TODAY
    )
    assert status == MatchRecordStatus.COMPLETE


def test_post_only_no_pre_at_all_is_incomplete():
    status = derive_match_record_status(official_post=object(), match_date=_PAST, today=_TODAY)
    assert status == MatchRecordStatus.INCOMPLETE


def test_retrospective_pre_and_post_is_retrospective_available():
    status = derive_match_record_status(
        retrospective_pre=object(), official_post=object(), match_date=_PAST, today=_TODAY
    )
    assert status == MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE


def test_official_pre_takes_priority_over_retrospective_when_both_present_with_post():
    status = derive_match_record_status(
        official_pre=object(), retrospective_pre=object(), official_post=object(),
        match_date=_PAST, today=_TODAY,
    )
    assert status == MatchRecordStatus.COMPLETE


def test_retrospective_pre_alone_without_post_is_retrospective_available():
    status = derive_match_record_status(
        retrospective_pre=object(), match_date=_PAST, today=_TODAY
    )
    assert status == MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE


def test_past_match_with_no_data_at_all_is_incomplete():
    status = derive_match_record_status(match_date=_PAST, today=_TODAY)
    assert status == MatchRecordStatus.INCOMPLETE


def test_match_date_equal_to_today_counts_as_played():
    status = derive_match_record_status(
        official_pre=object(), match_date=_TODAY, today=_TODAY
    )
    assert status == MatchRecordStatus.PLAYED_POST_PENDING


def test_unknown_match_date_never_counts_as_played():
    status = derive_match_record_status(official_pre=object(), match_date=None, today=_TODAY)
    assert status == MatchRecordStatus.PRE_OFFICIAL_IMPORTED


def test_all_six_statuses_are_reachable():
    scenarios = [
        derive_match_record_status(match_date=_FUTURE, today=_TODAY),
        derive_match_record_status(official_pre=object(), match_date=_FUTURE, today=_TODAY),
        derive_match_record_status(official_pre=object(), match_date=_PAST, today=_TODAY),
        derive_match_record_status(
            official_pre=object(), official_post=object(), match_date=_PAST, today=_TODAY
        ),
        derive_match_record_status(official_post=object(), match_date=_PAST, today=_TODAY),
        derive_match_record_status(
            retrospective_pre=object(), official_post=object(), match_date=_PAST, today=_TODAY
        ),
    ]
    assert set(scenarios) == set(MatchRecordStatus)


def test_localization_labels_present_for_every_status():
    from ht_coach_app.core.localization import configure_localization, t

    configure_localization("es")
    for status in MatchRecordStatus:
        label = t(f"match_record_status.{status.value}")
        assert label
        assert label != "No disponible"
    configure_localization("en")


def test_invariant_holds_exhaustively_across_every_input_combination():
    """Alpha 0.6.7, Part 16: COMPLETE requires official_post != None,
    checked against every realistic combination of evidence -- not
    just a couple of hand-picked cases."""
    from itertools import product

    presence_options = (None, object())
    date_options = (None, _PAST, _FUTURE, _TODAY)

    for official_pre, official_post, retrospective_pre, match_date in product(
        presence_options, presence_options, presence_options, date_options
    ):
        status = derive_match_record_status(
            official_pre=official_pre,
            official_post=official_post,
            retrospective_pre=retrospective_pre,
            match_date=match_date,
            today=_TODAY,
        )
        if status == MatchRecordStatus.COMPLETE:
            assert official_post is not None


def test_assert_status_invariants_raises_on_a_deliberately_broken_call():
    from engine.history.match_record_status import assert_status_invariants

    with pytest.raises(AssertionError):
        assert_status_invariants(MatchRecordStatus.COMPLETE, official_post=None)


def test_assert_status_invariants_passes_for_every_other_status():
    from engine.history.match_record_status import assert_status_invariants

    for status in MatchRecordStatus:
        if status == MatchRecordStatus.COMPLETE:
            continue
        assert_status_invariants(status, official_post=None)  # must not raise
