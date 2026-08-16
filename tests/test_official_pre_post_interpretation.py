from engine.history.official_ratings.comparison import (
    OfficialRatingComparison,
    SectorRatingComparison,
)
from engine.history.official_ratings.interpretation import (
    DIRECTION_DECLINED,
    DIRECTION_IMPROVED,
    DIRECTION_STABLE,
    MAGNITUDE_LARGE,
    MAGNITUDE_MODERATE,
    MAGNITUDE_SMALL,
    MAGNITUDE_STABLE,
    InterpretationThresholds,
    classify_change,
    generate_conclusions,
    interpret_comparison,
)


def _comparison(**deltas):
    sectors = tuple(
        SectorRatingComparison(
            sector=sector,
            official_pre_value=10.0,
            official_post_value=10.0 + (delta or 0),
            pre_vs_post_delta=delta,
        )
        for sector, delta in deltas.items()
    )
    return OfficialRatingComparison(sectors=sectors)


def test_briefs_own_worked_example_central_attack_large_decline():
    direction, magnitude = classify_change(-2.00)
    assert direction == DIRECTION_DECLINED
    assert magnitude == MAGNITUDE_LARGE


def test_exact_zero_is_stable():
    direction, magnitude = classify_change(0.00)
    assert direction == DIRECTION_STABLE
    assert magnitude == MAGNITUDE_STABLE


def test_small_change_below_stable_threshold_reads_as_stable():
    direction, magnitude = classify_change(0.10)
    assert direction == DIRECTION_STABLE


def test_small_magnitude_band():
    direction, magnitude = classify_change(0.30)
    assert direction == DIRECTION_IMPROVED
    assert magnitude == MAGNITUDE_SMALL


def test_moderate_magnitude_band():
    direction, magnitude = classify_change(0.60)
    assert magnitude == MAGNITUDE_MODERATE
    direction, magnitude = classify_change(-0.75)
    assert magnitude == MAGNITUDE_MODERATE


def test_large_magnitude_band_at_exactly_one():
    direction, magnitude = classify_change(1.00)
    assert magnitude == MAGNITUDE_LARGE


def test_negative_large_decline():
    direction, magnitude = classify_change(-1.5)
    assert direction == DIRECTION_DECLINED
    assert magnitude == MAGNITUDE_LARGE


def test_none_delta_produces_none_classification():
    direction, magnitude = classify_change(None)
    assert direction is None
    assert magnitude is None


def test_thresholds_are_typed_and_configurable():
    custom = InterpretationThresholds(stable_threshold=1.0, small_threshold=2.0, moderate_threshold=3.0)
    direction, magnitude = classify_change(0.5, custom)
    assert direction == DIRECTION_STABLE


def test_interpret_comparison_preserves_exact_values():
    comparison = _comparison(midfield=-0.5, central_attack=-2.0)
    interpreted = interpret_comparison(comparison)
    midfield = next(s for s in interpreted if s.sector == "midfield")
    assert midfield.pre_value == 10.0
    assert midfield.post_value == 9.5
    assert midfield.delta == -0.5


def test_conclusions_identify_largest_improvement_and_decline():
    comparison = _comparison(midfield=-0.5, central_attack=-2.0, right_attack=0.8)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    keys = {c.key: c for c in conclusions}
    assert "official_match_intelligence.conclusion.largest_decline" in keys
    assert keys["official_match_intelligence.conclusion.largest_decline"].params["sector"] == "central_attack"
    assert "official_match_intelligence.conclusion.largest_improvement" in keys
    assert keys["official_match_intelligence.conclusion.largest_improvement"].params["sector"] == "right_attack"


def test_conclusions_identify_stable_sectors():
    comparison = _comparison(midfield=0.0, left_attack=0.05, central_attack=-2.0)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    stable = next(c for c in conclusions if c.key == "official_match_intelligence.conclusion.stable_sectors")
    assert stable.params["count"] == 2


def test_conclusions_never_output_only_match_id_metadata():
    comparison = _comparison(midfield=-0.5)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    assert len(conclusions) >= 1
    assert all("match_id" not in c.key for c in conclusions)


def test_no_known_deltas_produces_no_data_conclusion():
    comparison = OfficialRatingComparison(
        sectors=(SectorRatingComparison(sector="midfield", pre_vs_post_delta=None),)
    )
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    assert len(conclusions) == 1
    assert conclusions[0].key == "official_match_intelligence.conclusion.no_data"


def test_missing_data_limitation_reported_when_some_sectors_unknown():
    comparison = OfficialRatingComparison(
        sectors=(
            SectorRatingComparison(sector="midfield", pre_vs_post_delta=-0.5),
            SectorRatingComparison(sector="right_defense", pre_vs_post_delta=None),
        )
    )
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    missing = next(
        (c for c in conclusions if c.key == "official_match_intelligence.conclusion.missing_data"),
        None,
    )
    assert missing is not None
    assert missing.params["count"] == 1


def test_missing_data_never_fabricates_a_delta():
    comparison = OfficialRatingComparison(
        sectors=(SectorRatingComparison(sector="right_defense", pre_vs_post_delta=None),)
    )
    interpreted = interpret_comparison(comparison)
    assert interpreted[0].direction is None
    assert interpreted[0].magnitude is None


def test_defensive_trend_reflects_majority_direction():
    comparison = _comparison(left_defense=-0.6, central_defense=-0.7, right_defense=0.3)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    assert any(
        c.key == "official_match_intelligence.conclusion.defensive_trend.declined"
        for c in conclusions
    )


def test_attacking_trend_tie_resolves_to_stable():
    comparison = _comparison(left_attack=0.6, central_attack=-0.6)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    assert any(
        c.key == "official_match_intelligence.conclusion.attacking_trend.stable"
        for c in conclusions
    )


def test_midfield_trend_reported_when_midfield_known():
    comparison = _comparison(midfield=-0.6)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    assert any(
        c.key == "official_match_intelligence.conclusion.midfield_trend.declined"
        for c in conclusions
    )


def test_conclusions_never_mention_causal_factors():
    comparison = _comparison(midfield=-2.0, central_attack=-1.5)
    interpreted = interpret_comparison(comparison)
    conclusions = generate_conclusions(interpreted)
    forbidden = ("stamina", "weather", "substitution", "cause", "because")
    for conclusion in conclusions:
        for word in forbidden:
            assert word not in conclusion.key.lower()


# --------------------------------------------------------------------------
# Service-layer wiring (MatchIntelligenceAppService)
# --------------------------------------------------------------------------

def test_service_interpreted_rows_and_conclusions_end_to_end(tmp_path):
    from engine.history.repository import HistoricalMatchRepository
    from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService

    pre = """[b]Team[/b] [matchid=770131822]
[table]
[tr][th]Defensa[/th][td]4.25[/td][td]7[/td][td]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3]7.25[/td][/tr]
[tr][th]Ataque[/th][td]7.75[/td][td]9.75[/td][td]8[/td][/tr]
[/table]
[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""
    post = pre.replace("9.75", "7.75")

    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    service.import_ratings(pre, slot="pre")
    service.import_ratings(post, slot="post")

    snapshot = service.latest_snapshot_with_official_data()
    rows = service.interpreted_pre_post_rows(snapshot)
    assert len(rows) == 7
    central_attack_row = next(r for r in rows if "9.75" == r[1])
    assert central_attack_row[3] == "-2.00"
    assert central_attack_row[4] == "declined"
    assert central_attack_row[5] == "large"


def test_service_conclusions_localize_sector_names_not_raw_keys(tmp_path):
    from engine.history.repository import HistoricalMatchRepository
    from ht_coach_app.core.localization import configure_localization
    from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService

    configure_localization("es")
    pre = """[b]Team[/b] [matchid=770131822]
[table]
[tr][th]Defensa[/th][td]4.25[/td][td]7[/td][td]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3]7.25[/td][/tr]
[tr][th]Ataque[/th][td]7.75[/td][td]9.75[/td][td]8[/td][/tr]
[/table]
[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""
    post = pre.replace("9.75", "7.75")

    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    service.import_ratings(pre, slot="pre")
    service.import_ratings(post, slot="post")

    snapshot = service.latest_snapshot_with_official_data()
    conclusions = service.pre_post_conclusions(snapshot)
    decline = next(c for c in conclusions if c.key == "official_match_intelligence.conclusion.largest_decline")
    assert "central_attack" not in decline.params["sector"]
    configure_localization("en")


def test_service_conclusions_empty_without_post(tmp_path):
    from engine.history.repository import HistoricalMatchRepository
    from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService

    pre = """[b]Team[/b] [matchid=770131822]
[table]
[tr][th]Defensa[/th][td]4.25[/td][td]7[/td][td]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3]7.25[/td][/tr]
[tr][th]Ataque[/th][td]7.75[/td][td]9.75[/td][td]8[/td][/tr]
[/table]
[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo"""

    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    service = MatchIntelligenceAppService(repository=repository)
    service.import_ratings(pre, slot="pre")

    snapshot = service.latest_snapshot_with_official_data()
    conclusions = service.pre_post_conclusions(snapshot)
    assert len(conclusions) == 1
    assert conclusions[0].key == "official_match_intelligence.conclusion.no_data"


def test_service_none_snapshot_returns_empty():
    from ht_coach_app.services.match_intelligence_service import MatchIntelligenceAppService

    service = MatchIntelligenceAppService(repository=None)
    assert service.interpreted_pre_post_rows(None) == ()
    assert service.pre_post_conclusions(None) == ()
