import pytest

from ht_coach_app.services.squad_intelligence_service import SquadIntelligenceAppService
from engine.squad_intelligence.models import PlayerIntelligenceReport
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
        make_player(name="Keeper One", goalkeeper=15, defending=2, playmaking=1, winger=1, passing=2, scoring=1, set_pieces=1),
        make_player(name="Defender One", defending=15, goalkeeper=1, playmaking=2, winger=2, passing=4, scoring=1, set_pieces=1),
        make_player(name="Midfielder One", playmaking=15, defending=3, goalkeeper=1, winger=4, passing=8, scoring=3, set_pieces=3, age=19),
        make_player(name="Winger One", winger=15, defending=2, goalkeeper=1, playmaking=4, passing=5, scoring=6, set_pieces=2),
        make_player(name="Forward One", scoring=15, defending=1, goalkeeper=1, playmaking=2, winger=3, passing=3, set_pieces=2),
    ]


def make_service(tmp_path):
    repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    weekly_service = WeeklyTrainingAppService(repository=repository)
    return SquadIntelligenceAppService(weekly_training_service=weekly_service)


def test_build_squad_context_reflects_positional_depth(tmp_path):
    service = make_service(tmp_path)
    players = make_squad()
    context = service.build_squad_context(players)

    assert context.roster_size == 5
    assert sum(context.positional_depth.values()) == 5


def test_build_squad_context_reads_active_training_type(tmp_path):
    service = make_service(tmp_path)
    context = service.build_squad_context(make_squad())
    assert context.active_training_type == "PLAYMAKING"


def test_build_player_context_computes_position_evidence(tmp_path):
    service = make_service(tmp_path)
    players = make_squad()
    midfielder = next(p for p in players if p.name == "Midfielder One")

    context = service.build_player_context(midfielder, players)

    assert context.position.best_position
    assert context.position.rank_in_best_position == 1
    assert context.position.candidates_in_best_position >= 1


def test_build_player_context_computes_training_evidence(tmp_path):
    service = make_service(tmp_path)
    players = make_squad()
    midfielder = next(p for p in players if p.name == "Midfielder One")

    context = service.build_player_context(midfielder, players)

    assert context.training.active_training_type == "PLAYMAKING"
    assert context.training.effect_for_best_position


def test_build_player_context_computes_salary_percentile(tmp_path):
    service = make_service(tmp_path)
    players = [
        make_player(name="Cheap", salary=100),
        make_player(name="Mid", salary=500),
        make_player(name="Expensive", salary=1000),
    ]
    cheap_context = service.build_player_context(players[0], players)
    expensive_context = service.build_player_context(players[2], players)

    assert cheap_context.salary_percentile_in_squad < expensive_context.salary_percentile_in_squad


def test_generate_report_end_to_end(tmp_path):
    service = make_service(tmp_path)
    players = make_squad()
    midfielder = next(p for p in players if p.name == "Midfielder One")

    report = service.generate_report(midfielder, players)

    assert isinstance(report, PlayerIntelligenceReport)
    assert report.player_name == "Midfielder One"


def test_generate_squad_reports_covers_every_player(tmp_path):
    service = make_service(tmp_path)
    players = make_squad()

    reports = service.generate_squad_reports(players)

    assert len(reports) == len(players)
    assert {r.player_name for r in reports} == {p.name for p in players}


def test_generate_squad_reports_never_raises_on_a_real_world_sized_roster(tmp_path):
    """Regression: PlayerAnalyzer.best_position() returns a
    (position, score) tuple, not a bare Position enum -- this crashed
    the first version of this service against a real CSV."""
    service = make_service(tmp_path)
    players = [make_player(name=f"Player {i}", age=18 + i % 15) for i in range(22)]
    reports = service.generate_squad_reports(players)
    assert len(reports) == 22


def test_missing_salary_produces_none_percentile(tmp_path):
    service = make_service(tmp_path)
    player = make_player()
    player.salary = None
    players = [player, make_player(name="Other")]
    context = service.build_player_context(player, players)
    assert context.salary_percentile_in_squad is None


def test_no_active_training_produces_empty_training_evidence(tmp_path):
    import json

    path = tmp_path / "planner.json"
    path.write_text(
        json.dumps({"active_training_type": "", "priorities": {}, "match_records": []}),
        encoding="utf-8",
    )
    repository = WeeklyTrainingRepository(path)
    weekly_service = WeeklyTrainingAppService(repository=repository)
    service = SquadIntelligenceAppService(weekly_training_service=weekly_service)

    players = make_squad()
    context = service.build_player_context(players[0], players)
    assert context.training.active_training_type == "" or not context.training.has_active_training
