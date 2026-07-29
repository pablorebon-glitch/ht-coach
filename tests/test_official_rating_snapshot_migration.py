from engine.history.models import HistoricalMatchSnapshot, MatchContext, stable_snapshot_id
from engine.history.official_ratings.parser import parse_official_ratings
from engine.history.repository import HistoricalMatchRepository

SAMPLE_TEXT = """
Formation: 2-5-3
Central defense: 7.00
Left defense: 4.25
Right defense: 3.75
Midfield: 7.25
Left attack: 7.75
Central attack: 9.75
Right attack: 8.00
Tactic: Attack in the middle
Tactic level: world class (13)
Team Attitude: Normal
"""


def test_legacy_snapshot_dict_without_official_pre_post_loads_cleanly():
    """Simulates a snapshot saved before this sprint: no official_pre or
    official_post keys at all in the JSON."""
    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(match_date="2026-06-01"),
    )
    legacy_data = snapshot.to_dict()
    del legacy_data["official_pre"]
    del legacy_data["official_post"]

    reloaded = HistoricalMatchSnapshot.from_dict(legacy_data)

    assert reloaded.official_pre is None
    assert reloaded.official_post is None
    assert reloaded.snapshot_id == snapshot.snapshot_id


def test_schema_version_unchanged_by_this_sprint():
    """The new fields are purely additive with a safe default (None), so
    no schema version bump was needed — confirm that's still true."""
    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(match_date="2026-06-01"),
    )
    assert snapshot.schema_version == 1


def test_prediction_pre_and_post_all_coexist(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    from engine.history.models import PredictionSnapshot, SectorRatings

    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(match_date="2026-07-20"),
        predictions=PredictionSnapshot(ratings=SectorRatings(midfield=7.0)),
    )
    repository.save(snapshot)

    pre = parse_official_ratings(SAMPLE_TEXT)
    post = parse_official_ratings(SAMPLE_TEXT.replace("7.25", "7.50"))
    snapshot = snapshot.with_updates(official_pre=pre, official_post=post)
    repository.save(snapshot)

    reloaded = repository.get(snapshot.snapshot_id)
    assert reloaded.predictions.ratings.midfield == 7.0
    assert reloaded.official_pre.ratings.midfield == 7.25
    assert reloaded.official_post.ratings.midfield == 7.50
    # none replaces another
    assert reloaded.predictions.ratings.midfield != reloaded.official_pre.ratings.midfield
    assert reloaded.official_pre.ratings.midfield != reloaded.official_post.ratings.midfield


def test_official_pre_and_post_round_trip_through_json_file(tmp_path):
    path = tmp_path / "snapshots.json"
    repository = HistoricalMatchRepository(path)
    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(match_date="2026-07-20"),
    )
    pre = parse_official_ratings(SAMPLE_TEXT)
    snapshot = snapshot.with_updates(official_pre=pre)
    repository.save(snapshot)

    assert path.exists()
    fresh_repository = HistoricalMatchRepository(path)
    reloaded = fresh_repository.get(snapshot.snapshot_id)
    assert reloaded.official_pre.ratings.midfield == 7.25
    assert reloaded.official_pre.formation.label == "2-5-3"
    assert reloaded.official_pre.tactic.level == 13.0


def test_official_result_and_official_pre_post_are_independent_fields():
    """official_result (existing, post-match outcome/goals) and the new
    official_pre/official_post (Copy Ratings captures) are separate —
    setting one must not affect the other."""
    from engine.history.models import OfficialResultSnapshot

    snapshot = HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=MatchContext(match_date="2026-07-20"),
        official_result=OfficialResultSnapshot(goals_for=2, goals_against=1),
    )
    pre = parse_official_ratings(SAMPLE_TEXT)
    updated = snapshot.with_updates(official_pre=pre)

    assert updated.official_result.goals_for == 2
    assert updated.official_pre.ratings.midfield == 7.25
