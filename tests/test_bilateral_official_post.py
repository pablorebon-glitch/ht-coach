from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.official_ratings.models import POST_BILATERAL, POST_INDIVIDUAL
from engine.history.official_ratings.parser import (
    detect_post_format,
    parse_official_match_post,
    parse_official_post_ratings,
)
from engine.history.official_ratings.scenario_drift import (
    DRIFT_MEDIUM,
    compare_expected_opponent_to_actual_post,
)
from engine.history.repository import HistoricalMatchRepository
from engine.ratings.calibration_samples import (
    OPPONENT_SCENARIO_PAIR,
    POST_VALIDATION_PAIR,
    build_rating_calibration_samples,
)
from ht_coach_app.services.official_rating_service import POST, OfficialRatingImportService
from models.tactic import Tactic


SAN_BASON_BILATERAL_POST = """[table][tr][th][matchid=770131829][/th][th colspan=2]Hit'em up - 7 [teamid=2819540][/th][th colspan=2]san bason - 1 [teamid=3414681][/th][/tr]
[tr][th]Midfield[/th][td]solid[/td][td align=right]7.00[/td][td]weak[/td][td align=right]3.25[/td][/tr]
[tr][th]Right Defense[/th][td]weak[/td][td align=right]4.00[/td][td]poor[/td][td align=right]3.25[/td][/tr]
[tr][th]Central Defense[/th][td]passable[/td][td align=right]6.25[/td][td]weak[/td][td align=right]4.75[/td][/tr]
[tr][th]Left Defense[/th][td]weak[/td][td align=right]4.00[/td][td]inadequate[/td][td align=right]5.00[/td][/tr]
[tr][th]Right Attack[/th][td]solid[/td][td align=right]7.75[/td][td]weak[/td][td align=right]4.25[/td][/tr]
[tr][th]Central Attack[/th][td]outstanding[/td][td align=right]10.25[/td][td]poor[/td][td align=right]3.00[/td][/tr]
[tr][th]Left Attack[/th][td]excellent[/td][td align=right]8.00[/td][td]poor[/td][td align=right]3.75[/td][/tr]
[tr][th colspan=5]Indirect Set Pieces[/th][/tr]
[tr][th]Defense[/th][td]passable[/td][td align=right]6.00[/td][td]inadequate[/td][td align=right]5.00[/td][/tr]
[tr][th]Attack[/th][td]inadequate[/td][td align=right]5.50[/td][td]inadequate[/td][td align=right]5.00[/td][/tr]
[tr][th colspan=5]Game Plan[/th][/tr]
[tr][th]Tactic[/th][td colspan=2]Attack through the middle[/td][td colspan=2]Normal[/td][/tr]
[tr][th]Tactic Level[/th][td]supernatural[/td][td align=right]14[/td][td colspan=2]none[/td][/tr]
[tr][th]Playing Style[/th][td colspan=2]100% offensive[/td][td colspan=2]neutral[/td][/tr]
[/table]"""


SAN_BASON_INDIVIDUAL_POST = """
[b]Hit'em up[/b] [matchid=770131829]
Midfield: 7.00
Right Defense: 4.00
Central Defense: 6.25
Left Defense: 4.00
Right Attack: 7.75
Central Attack: 10.25
Left Attack: 8.00
Indirect Set Pieces (Defense): 6.00
Indirect Set Pieces (Attack): 5.50
Tactic: Attack through the middle
Tactic level: supernatural (14)
Playing Style: 100% offensive
"""


def _record():
    return HistoricalMatchSnapshot(
        snapshot_id="match-san-bason",
        match_context=MatchContext(
            official_match_id="770131829",
            opponent=OpponentReference(opponent_name="san bason"),
        ),
    )


def test_bilateral_post_detected_from_two_team_headers():
    assert detect_post_format(SAN_BASON_BILATERAL_POST) == POST_BILATERAL
    assert detect_post_format(SAN_BASON_INDIVIDUAL_POST) == POST_INDIVIDUAL


def test_san_bason_bilateral_fixture_parses_exactly():
    result = parse_official_match_post(SAN_BASON_BILATERAL_POST)

    assert result.match_id == "770131829"
    assert result.source_format == POST_BILATERAL
    assert result.our_team_post.team_name == "Hit'em up"
    assert result.our_team_post.team_id == "2819540"
    assert result.our_team_post.score == 7
    assert result.our_team_post.ratings.midfield == 7.00
    assert result.our_team_post.ratings.right_defense == 4.00
    assert result.our_team_post.ratings.central_defense == 6.25
    assert result.our_team_post.ratings.left_defense == 4.00
    assert result.our_team_post.ratings.right_attack == 7.75
    assert result.our_team_post.ratings.central_attack == 10.25
    assert result.our_team_post.ratings.left_attack == 8.00
    assert result.our_team_post.ratings.indirect_defense == 6.00
    assert result.our_team_post.ratings.indirect_attack == 5.50
    assert result.our_team_post.canonical_tactic == Tactic.ATTACK_IN_MIDDLE.value
    assert result.our_team_post.tactic_level == 14
    assert result.our_team_post.playing_style == "100% offensive"

    opponent = result.opponent_team_post
    assert opponent.team_name == "san bason"
    assert opponent.team_id == "3414681"
    assert opponent.score == 1
    assert opponent.ratings.midfield == 3.25
    assert opponent.ratings.right_defense == 3.25
    assert opponent.ratings.central_defense == 4.75
    assert opponent.ratings.left_defense == 5.00
    assert opponent.ratings.right_attack == 4.25
    assert opponent.ratings.central_attack == 3.00
    assert opponent.ratings.left_attack == 3.75
    assert opponent.ratings.indirect_defense == 5.00
    assert opponent.ratings.indirect_attack == 5.00
    assert opponent.canonical_tactic == Tactic.NORMAL.value
    assert opponent.tactic_level is None
    assert opponent.playing_style == "neutral"


def test_legacy_post_parser_returns_our_side_from_bilateral():
    snapshot = parse_official_post_ratings(SAN_BASON_BILATERAL_POST)

    assert snapshot.team_name == "Hit'em up"
    assert snapshot.team_id == "2819540"
    assert snapshot.score == 7
    assert snapshot.ratings.midfield == 7.00
    assert snapshot.detected_format == POST_BILATERAL


def test_bilateral_import_enriches_existing_individual_post_without_duplicate(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "history.json")
    repository.save(_record())
    service = OfficialRatingImportService(repository=repository)

    first = service.import_ratings("match-san-bason", SAN_BASON_INDIVIDUAL_POST, slot=POST)
    enriched = service.import_ratings("match-san-bason", SAN_BASON_BILATERAL_POST, slot=POST)

    assert first.snapshot.snapshot_id == enriched.snapshot.snapshot_id
    assert len(repository.list_all()) == 1
    reloaded = repository.get("match-san-bason")
    assert reloaded.official_post.team_name == "Hit'em up"
    assert reloaded.official_match_post.opponent_team_post.team_name == "san bason"
    assert reloaded.match_context.opponent.opponent_name == "san bason"


def test_repeated_bilateral_import_is_idempotent(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "history.json")
    repository.save(_record())
    service = OfficialRatingImportService(repository=repository)

    service.import_ratings("match-san-bason", SAN_BASON_BILATERAL_POST, slot=POST)
    service.import_ratings("match-san-bason", SAN_BASON_BILATERAL_POST, slot=POST)

    assert len(repository.list_all()) == 1
    reloaded = repository.get("match-san-bason")
    assert reloaded.official_match_post.opponent_team_post.score == 1


def test_bilateral_first_individual_later_does_not_remove_opponent_context(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "history.json")
    repository.save(_record())
    service = OfficialRatingImportService(repository=repository)

    service.import_ratings("match-san-bason", SAN_BASON_BILATERAL_POST, slot=POST)
    service.import_ratings("match-san-bason", SAN_BASON_INDIVIDUAL_POST, slot=POST)

    reloaded = repository.get("match-san-bason")
    assert reloaded.official_match_post.opponent_team_post.team_name == "san bason"
    assert len(repository.list_all()) == 1


def test_bilateral_post_persists_through_repository_reload(tmp_path):
    path = tmp_path / "history.json"
    repository = HistoricalMatchRepository(path)
    repository.save(_record())
    OfficialRatingImportService(repository=repository).import_ratings(
        "match-san-bason",
        SAN_BASON_BILATERAL_POST,
        slot=POST,
    )

    reloaded = HistoricalMatchRepository(path).get("match-san-bason")
    assert reloaded.official_match_post.source_format == POST_BILATERAL
    assert reloaded.official_match_post.opponent_team_post.ratings.midfield == 3.25


def test_scenario_drift_uses_ratings_not_score():
    post = parse_official_match_post(SAN_BASON_BILATERAL_POST)

    class expected:
        class ratings:
            midfield = 5.25
            right_defense = 4.25
            central_defense = 5.75
            left_defense = 6.00
            right_attack = 5.25
            central_attack = 4.25
            left_attack = 5.00

        canonical_tactic = Tactic.NORMAL.value
        style = "neutral"

    drift = compare_expected_opponent_to_actual_post(expected, post.opponent_team_post)

    assert drift.overall_magnitude == DRIFT_MEDIUM
    assert "más débil" in drift.explanation


def test_bilateral_post_generates_secondary_validation_samples_only():
    post = parse_official_match_post(SAN_BASON_BILATERAL_POST)

    class record:
        snapshot_id = "match-san-bason"
        official_post = post.our_snapshot()
        official_match_post = post

        class match_context:
            official_match_id = "770131829"

        class predictions:
            class ratings:
                midfield = 7.1
                right_defense = 4.1
                central_defense = 6.1
                left_defense = 4.1
                right_attack = 7.6
                central_attack = 10.1
                left_attack = 7.9

    samples = build_rating_calibration_samples([record])

    post_samples = [sample for sample in samples if sample.sample_type == POST_VALIDATION_PAIR]
    opponent_samples = [sample for sample in samples if sample.sample_type == OPPONENT_SCENARIO_PAIR]
    assert len(post_samples) == 7
    assert opponent_samples == []
    assert {sample.sample_id for sample in post_samples} == {
        f"match-san-bason:{POST_VALIDATION_PAIR}:{sample.sector}:v1"
        for sample in post_samples
    }
