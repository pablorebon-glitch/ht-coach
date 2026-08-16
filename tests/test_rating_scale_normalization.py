import pytest

from engine.evaluators.match_evaluator import MatchEvaluator
from engine.ratings.calibration_samples import (
    PRIMARY_PRE,
    SECONDARY_POST,
    build_rating_calibration_samples,
)
from engine.ratings.rating_scale_normalizer import (
    BOOTSTRAP_CALIBRATION_VERSION,
    RatingScaleNormalizer,
    bootstrap_calibration_model,
    rebuild_rating_calibration,
    validate_compatible_ratings,
)
from ht_coach_app.persistence.rating_calibration_repository import (
    RatingCalibrationRepository,
)
from models.rating_scale import RatingScale, RatingSource
from models.team_ratings import TeamRatings


def _internal_ratings():
    return TeamRatings(
        left_defense=16.45,
        central_defense=28.32,
        right_defense=15.89,
        midfield=39.68,
        left_attack=25.92,
        central_attack=39.12,
        right_attack=26.56,
        rating_scale=RatingScale.INTERNAL_CONTRIBUTION,
        rating_source=RatingSource.LINEUP_ENGINE,
    )


def _la_rocha():
    return TeamRatings(
        left_defense=8.50,
        central_defense=13.00,
        right_defense=7.50,
        midfield=5.75,
        left_attack=4.25,
        central_attack=7.00,
        right_attack=4.00,
        rating_scale=RatingScale.HT_OFFICIAL_DECIMAL,
        rating_source=RatingSource.OPPONENT_IMPORT,
    )


def test_mixed_scales_are_rejected_before_match_evaluation():
    with pytest.raises(ValueError, match="rating_scale_mismatch"):
        MatchEvaluator.evaluate(_internal_ratings(), _la_rocha())


def test_internal_ratings_normalize_to_ht_compatible_estimate_without_mutating_original():
    internal = _internal_ratings()
    calibrated = RatingScaleNormalizer().normalize_own_ratings(internal)

    assert internal.midfield == pytest.approx(39.68)
    assert internal.rating_scale == RatingScale.INTERNAL_CONTRIBUTION
    assert calibrated.ratings.rating_scale == RatingScale.HT_CALIBRATED_ESTIMATE
    assert calibrated.ratings.midfield == pytest.approx(7.75)
    assert calibrated.calibration_version == BOOTSTRAP_CALIBRATION_VERSION
    assert calibrated.confidence.value == "low"


def test_normalized_la_rocha_fixture_no_longer_uses_39_vs_575_chance_share():
    normalizer = RatingScaleNormalizer()
    own, opponent = normalizer.normalize_matchup(_internal_ratings(), _la_rocha())

    result = MatchEvaluator.evaluate(own.ratings, opponent)

    assert result.chance_probability < 0.80
    assert result.chance_probability == pytest.approx(0.7100195433528766)
    assert result.expected_goals < 4.0
    assert result.opponent_expected_goals > 1.0


def test_la_rocha_official_candidate_b_remains_better_than_candidate_a():
    opponent = _la_rocha()
    candidate_a = TeamRatings(
        left_defense=4.25,
        central_defense=5.25,
        right_defense=4.25,
        midfield=6.75,
        left_attack=9.50,
        central_attack=12.50,
        right_attack=9.25,
    )
    candidate_b = TeamRatings(
        left_defense=4.25,
        central_defense=5.25,
        right_defense=4.50,
        midfield=7.75,
        left_attack=9.25,
        central_attack=12.25,
        right_attack=9.00,
    )

    a = MatchEvaluator.evaluate(candidate_a, opponent.without_metadata())
    b = MatchEvaluator.evaluate(candidate_b, opponent.without_metadata())

    assert b.chance_probability > a.chance_probability
    assert b.expected_goals > a.expected_goals
    assert b.opponent_expected_goals < a.opponent_expected_goals


def test_calibration_repository_persists_and_reloads_model(tmp_path):
    path = tmp_path / "rating_calibration.json"
    repository = RatingCalibrationRepository(path)
    model = bootstrap_calibration_model()

    repository.save(model)
    loaded = repository.load()

    assert loaded.calibration_version == model.calibration_version
    assert loaded.sector_mappings["midfield"].slope == pytest.approx(
        model.sector_mappings["midfield"].slope
    )


def test_validate_compatible_ratings_rejects_missing_or_mixed_metadata():
    with pytest.raises(ValueError, match="rating_scale_missing"):
        validate_compatible_ratings(TeamRatings(), _la_rocha())
    with pytest.raises(ValueError, match="rating_scale_mismatch"):
        validate_compatible_ratings(_internal_ratings(), _la_rocha())


class _Record:
    snapshot_id = "match-1"

    class predictions:
        ratings = TeamRatings(
            midfield=40.0,
            left_defense=16.0,
            central_defense=28.0,
            right_defense=16.0,
            left_attack=26.0,
            central_attack=39.0,
            right_attack=27.0,
        )

    class tactical_setup:
        formation = "2-5-3"
        selected_tactic = "Attack on Wings"

    class official_pre:
        captured_at = "2026-08-16T00:00:00Z"
        ratings = TeamRatings(
            midfield=7.75,
            left_defense=4.25,
            central_defense=5.25,
            right_defense=4.50,
            left_attack=9.25,
            central_attack=12.25,
            right_attack=9.00,
        )

    class official_post:
        captured_at = "2026-08-17T00:00:00Z"
        class ratings:
            midfield = 7.50
            left_defense = None
            central_defense = None
            right_defense = None
            left_attack = None
            central_attack = None
            right_attack = None


def test_pre_and_post_calibration_samples_are_kept_separate():
    samples = build_rating_calibration_samples([_Record()])

    pre = [sample for sample in samples if sample.source == PRIMARY_PRE]
    post = [sample for sample in samples if sample.source == SECONDARY_POST]

    assert len(pre) == 7
    assert len(post) == 1
    assert pre[0].match_record_id == "match-1"


def test_rebuild_rating_calibration_falls_back_when_samples_are_too_sparse():
    model = rebuild_rating_calibration([_Record()], minimum_samples_per_sector=3)

    assert model.calibration_version == BOOTSTRAP_CALIBRATION_VERSION
    assert model.confidence.value == "low"
