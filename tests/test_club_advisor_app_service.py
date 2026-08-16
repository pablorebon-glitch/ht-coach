from ht_coach_app.services.club_advisor_service import ClubAdvisorAppService
from engine.club_advisor.models import ClubAdvisorReport
from engine.weekly_training.persistence import WeeklyTrainingRepository
from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService
from models.player import Player


def make_player(**overrides):
    base = dict(
        name="Test Player", age=22, days=50, speciality="", form=6, stamina=7,
        goalkeeper=1, defending=5, playmaking=5, winger=5, passing=5, scoring=5,
        set_pieces=4, experience=5, leadership=4, tsi=5000, salary=1000,
    )
    base.update(overrides)
    return Player(**base)


def make_squad():
    return [
        make_player(name="Keeper", goalkeeper=15, defending=2, playmaking=1, winger=1, passing=2, scoring=1, set_pieces=1),
        make_player(name="Defender", defending=15, goalkeeper=1, playmaking=2, winger=2, passing=4, scoring=1, set_pieces=1),
        make_player(name="Midfielder", playmaking=15, defending=3, goalkeeper=1, winger=4, passing=8, scoring=3, set_pieces=3, age=19),
        make_player(name="Winger", winger=15, defending=2, goalkeeper=1, playmaking=4, passing=5, scoring=6, set_pieces=2),
        make_player(name="Forward", scoring=15, defending=1, goalkeeper=1, playmaking=2, winger=3, passing=3, set_pieces=2),
    ]


def make_service(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=repository)
    return ClubAdvisorAppService(weekly_training_service=weekly_service)


def test_build_context_from_real_roster(tmp_path):
    service = make_service(tmp_path)
    context = service.build_context(make_squad())
    assert len(context.squad_reports) == 5
    assert context.active_training_type == "PLAYMAKING"


def test_generate_report_end_to_end(tmp_path):
    service = make_service(tmp_path)
    report = service.generate_report(make_squad())
    assert isinstance(report, ClubAdvisorReport)


def test_generate_report_with_realistic_sized_roster_never_crashes(tmp_path):
    service = make_service(tmp_path)
    players = [make_player(name=f"Player {i}", age=18 + i % 15) for i in range(22)]
    report = service.generate_report(players)
    assert isinstance(report, ClubAdvisorReport)


def test_generate_report_with_empty_roster_does_not_crash(tmp_path):
    service = make_service(tmp_path)
    report = service.generate_report([])
    assert isinstance(report, ClubAdvisorReport)
    from engine.club_advisor.enums import ClubLimitationType

    assert ClubLimitationType.EMPTY_ROSTER in report.limitations
