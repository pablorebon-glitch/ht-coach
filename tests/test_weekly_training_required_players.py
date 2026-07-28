import os
from datetime import date
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from engine.weekly_training.models import (
    MatchRole,
    MatchStatus,
    TrainingPriority,
    TrainingPriorityRecord,
    WeeklyMatchLineupEntry,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_rules import PlaymakingTrainingRules, assumed_confidence
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from models.player import Player


def player(name, playmaking=5):
    return Player(
        name=name,
        age=23,
        days=12,
        speciality="",
        form=7,
        stamina=7,
        goalkeeper=1,
        defending=5,
        playmaking=playmaking,
        winger=5,
        passing=5,
        scoring=5,
        set_pieces=4,
        experience=5,
        leadership=4,
        tsi=1000 + playmaking,
        salary=1000,
        injury=None,
    )


def entry_for(player_obj, position, minutes=90, match_id="m1"):
    return WeeklyMatchLineupEntry(
        player_id=player_training_id(player_obj),
        player_name=player_obj.name,
        slot_id=f"{position}:1",
        position=position,
        side="CENTER",
        played_minutes=Decimal(str(minutes)),
    )


def played_record(entries, match_id="m1", minutes_known=False):
    rules = PlaymakingTrainingRules()
    return WeeklyMatchRecord(
        match_id=match_id,
        match_date=date(2026, 7, 19),
        match_role=MatchRole.FIRST_WEEKLY_MATCH,
        formation="3-5-2",
        lineup=tuple(entries),
        planned_or_played=MatchStatus.PLAYED,
        minutes_known=minutes_known,
        training_exposure_entries=tuple(
            rules.exposure_for_entry(
                match_id,
                entry,
                "test",
                assumed_confidence(minutes_known),
            )
            for entry in entries
        ),
    )


def make_service(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    return WeeklyTrainingAppService(repository=repository)


def test_required_ids_include_players_with_no_minutes_logged_yet(tmp_path):
    service = make_service(tmp_path)
    required_100 = player("Required100")
    required_50 = player("Required50")
    no_priority = player("NoPriority")

    service.save_priority(required_100, TrainingPriority.REQUIRED_100.value)
    service.save_priority(required_50, TrainingPriority.REQUIRED_50.value)
    service.save_priority(no_priority, TrainingPriority.NO_PRIORITY.value)

    required_ids = service.required_player_ids_for_match()

    assert player_training_id(required_100) in required_ids
    assert player_training_id(required_50) in required_ids
    assert player_training_id(no_priority) not in required_ids


def test_required_100_player_already_covered_by_first_match_is_excluded(tmp_path):
    service = make_service(tmp_path)
    covered = player("AlreadyPlayedFullMatch")
    still_needed = player("StillNeedsToPlay")

    service.save_priority(covered, TrainingPriority.REQUIRED_100.value)
    service.save_priority(still_needed, TrainingPriority.REQUIRED_100.value)

    state = service.load_state()
    record = played_record(
        [entry_for(covered, "INNER_MIDFIELDER", minutes=90)]
    )
    service._repository.add_match_record(state, record)

    required_ids = service.required_player_ids_for_match()

    # Covered player already trained a full 90 effective minutes at
    # INNER_MIDFIELDER (factor 1.0), so their target is met and they no
    # longer need to be forced into the second match.
    assert player_training_id(covered) not in required_ids
    assert player_training_id(still_needed) in required_ids


def test_required_50_player_partially_covered_still_required(tmp_path):
    service = make_service(tmp_path)
    partially_covered = player("PartiallyCovered")

    service.save_priority(partially_covered, TrainingPriority.REQUIRED_50.value)

    state = service.load_state()
    # Played as a Winger (factor 0.5): 90 real minutes * 0.5 = 45
    # effective minutes, which exactly meets the 45-minute Required 50%
    # target.
    record = played_record(
        [entry_for(partially_covered, "WINGER", minutes=90)]
    )
    service._repository.add_match_record(state, record)

    required_ids = service.required_player_ids_for_match()

    assert player_training_id(partially_covered) not in required_ids


def test_second_match_record_updates_coverage(tmp_path):
    from datetime import date as date_cls

    from ht_coach_app.services.formation_board_service import FormationBoardMapper
    from ht_coach_app.services.match_workspace_service import (
        FormationAnalysisResult,
        LineupPlayerResult,
        MatchAnalysisResult,
    )

    service = make_service(tmp_path)
    names = ["GK", "CD1", "CD2", "CD3", "WG1", "WG2", "IM1", "IM2", "IM3", "FW1", "FW2"]
    positions = [
        "GOALKEEPER", "CENTRAL_DEFENDER", "CENTRAL_DEFENDER", "CENTRAL_DEFENDER",
        "WINGER", "WINGER", "INNER_MIDFIELDER", "INNER_MIDFIELDER",
        "INNER_MIDFIELDER", "FORWARD", "FORWARD",
    ]
    sides = ["CENTER"] * 4 + ["LEFT", "RIGHT"] + ["CENTER"] * 5
    roster = [player(n) for n in names]
    lineup = [
        LineupPlayerResult(
            number=i + 1, position=positions[i], side=sides[i],
            order="NORMAL", order_side="", player_name=names[i],
        )
        for i in range(11)
    ]
    formation_result = FormationAnalysisResult(
        formation_name="3-5-2", recommended_tactic="NORMAL", tactic_level=0.0,
        win_probability=0.6, draw_probability=0.2, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.0,
        lineup=lineup, is_recommended=True,
    )
    result = MatchAnalysisResult(
        player_count=11, opponent_name="Rival Copa", formations=[formation_result]
    )
    board = FormationBoardMapper().to_board(result.recommended_formation)

    service.record_second_match(board, opponent_name="Rival Copa", roster_players=roster)

    record = service.second_match_record()
    assert record is not None
    assert record.opponent_name == "Rival Copa"

    coverage = {row.player_name: row for row in service.coverage(roster)}
    assert coverage["IM1"].planned_exposure == 100
    assert coverage["WG1"].planned_exposure == 50.0
    assert coverage["FW1"].planned_exposure == 0

    # Saving again without deleting/replacing first must fail loudly,
    # same contract as the first match, so the UI can offer to replace.
    with pytest.raises(ValueError):
        service.record_second_match(board, opponent_name="Rival Copa", roster_players=roster)

    service.replace_second_match(board, opponent_name="Other Rival", roster_players=roster)
    assert service.second_match_record().opponent_name == "Other Rival"


def test_active_training_rules_returns_playmaking_provider(tmp_path):
    service = make_service(tmp_path)
    rules = service.active_training_rules()
    assert rules is not None
    assert rules.supports("PLAYMAKING")


def test_player_identity_survives_days_and_tsi_drift(tmp_path):
    """Reproduces the real bug: a player's 'days' and 'tsi' change almost
    every week in Hattrick, which used to make a saved Required priority
    silently stop matching that same player a few days later."""
    service = make_service(tmp_path)
    week_one = player("Jae-Pyo Yang", playmaking=5)
    # simulate the same real player, a week later: age/name/salary the
    # same, but days and tsi have drifted (as they always do in Hattrick).
    week_two = Player(
        name=week_one.name,
        age=week_one.age,
        days=week_one.days + 6,
        speciality=week_one.speciality,
        form=week_one.form,
        stamina=week_one.stamina,
        goalkeeper=week_one.goalkeeper,
        defending=week_one.defending,
        playmaking=week_one.playmaking,
        winger=week_one.winger,
        passing=week_one.passing,
        scoring=week_one.scoring,
        set_pieces=week_one.set_pieces,
        experience=week_one.experience,
        leadership=week_one.leadership,
        tsi=week_one.tsi + 90,
        salary=week_one.salary,
    )

    service.save_priority(week_one, TrainingPriority.REQUIRED_100.value)
    required_ids = service.required_player_ids_for_match()

    assert player_training_id(week_two) in required_ids


def test_duplicate_names_still_disambiguated_by_salary(tmp_path):
    from engine.weekly_training.player_identity import player_training_id as pid

    first = player("Same Name")
    second = Player(
        name=first.name,
        age=first.age,
        days=first.days,
        speciality=first.speciality,
        form=first.form,
        stamina=first.stamina,
        goalkeeper=first.goalkeeper,
        defending=first.defending,
        playmaking=first.playmaking,
        winger=first.winger,
        passing=first.passing,
        scoring=first.scoring,
        set_pieces=first.set_pieces,
        experience=first.experience,
        leadership=first.leadership,
        tsi=first.tsi,
        salary=first.salary + 500,
    )

    assert pid(first) != pid(second)


def test_multiple_legacy_entries_for_same_player_use_the_most_recent(tmp_path):
    """Reproduces the real bug: a player edited more than once before the
    identity fix ends up with several legacy 5-part
    name|age|days|tsi|salary records. The most recently saved one (the
    highest 'days' value) must win, not silently fall back to
    NO_PRIORITY just because there's more than one candidate."""
    service = make_service(tmp_path)
    current = player("Multi Edited Player")

    def legacy_record(days, tsi, priority):
        legacy_id = "|".join(
            [
                current.name.casefold(),
                str(current.age),
                str(days),
                str(tsi),
                str(current.salary),
            ]
        )
        return TrainingPriorityRecord(
            player_id=legacy_id,
            player_name=current.name,
            priority=priority,
        )

    state = service.load_state()
    state = service._repository.save_priority(
        state, legacy_record(days=10, tsi=1000, priority=TrainingPriority.REST)
    )
    state = service._repository.save_priority(
        state,
        legacy_record(days=17, tsi=1090, priority=TrainingPriority.REQUIRED_100),
    )

    rows = service.priority_rows([current])
    row = next(r for r in rows if r.player_name == current.name)
    assert row.priority == TrainingPriority.REQUIRED_100

    required_ids = service.required_player_ids_for_match()
    assert player_training_id(current) in required_ids


def test_stale_week_rolls_over_automatically_on_load(tmp_path):
    from engine.weekly_training.training_week import active_training_week

    service = make_service(tmp_path)
    state = service.load_state()
    stale_week = active_training_week(today=date(2026, 7, 20))
    service._repository.save(
        state.__class__(
            active_training_type=state.active_training_type,
            active_week=stale_week,
            priorities=state.priorities,
            match_records=state.match_records,
            archived_weeks=state.archived_weeks,
        )
    )

    reloaded = service.load_state()

    assert reloaded.active_week.week_id != stale_week.week_id
    assert len(reloaded.archived_weeks) == 1


def test_first_match_record_ignores_stale_previous_week_record(tmp_path):
    from engine.weekly_training.training_week import active_training_week

    service = make_service(tmp_path)
    state = service.load_state()
    stale_week = active_training_week(today=date(2026, 7, 20))
    old_record = WeeklyMatchRecord(
        match_id=f"{stale_week.week_id}:first",
        match_date=date(2026, 7, 19),
        match_role=MatchRole.FIRST_WEEKLY_MATCH,
        formation="2-5-3",
        lineup=(),
        planned_or_played=MatchStatus.PLAYED,
        opponent_name="Old Rival",
    )
    service._repository.save(
        state.__class__(
            active_training_type=state.active_training_type,
            active_week=stale_week,
            priorities=state.priorities,
            match_records=(old_record,),
            archived_weeks=state.archived_weeks,
        )
    )

    # Rolling over to the current week should stop surfacing last week's
    # first-match record as if it belonged to the new week.
    assert service.first_match_record() is None
