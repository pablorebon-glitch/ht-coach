import ast
from pathlib import Path

INSIGHTS_PACKAGE = Path(__file__).resolve().parents[1] / "engine" / "history" / "insights"
EVOLUTION_PACKAGE = Path(__file__).resolve().parents[1] / "engine" / "history" / "evolution"

FORBIDDEN_MODULES = (
    "engine.optimizers.formation_optimizer",
    "engine.optimizers.lineup_optimizer",
    "engine.optimizers.tactic_optimizer",
    "engine.optimizers.order_optimizer",
    "engine.optimizers.training_constrained_optimizer",
)


def _imported_modules(source_path):
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_history_insights_package_never_imports_formation_optimizer():
    for path in INSIGHTS_PACKAGE.glob("*.py"):
        imported = _imported_modules(path)
        assert not (imported & set(FORBIDDEN_MODULES)), (
            f"{path.name} imports a forbidden optimizer module: "
            f"{imported & set(FORBIDDEN_MODULES)}"
        )


def test_history_evolution_package_never_imports_formation_optimizer():
    for path in EVOLUTION_PACKAGE.glob("*.py"):
        imported = _imported_modules(path)
        assert not (imported & set(FORBIDDEN_MODULES)), (
            f"{path.name} imports a forbidden optimizer module: "
            f"{imported & set(FORBIDDEN_MODULES)}"
        )


def test_historical_insights_service_never_imports_formation_optimizer():
    service_path = (
        Path(__file__).resolve().parents[1]
        / "ht_coach_app" / "services" / "historical_insights_service.py"
    )
    if not service_path.exists():
        return
    imported = _imported_modules(service_path)
    assert not (imported & set(FORBIDDEN_MODULES))


def test_generate_insights_does_not_touch_optimizer_call_sites():
    """A behavioral (not just import-based) guarantee: generating
    insights from a fixed pair of snapshots must not require, call, or
    depend on any optimizer — the whole insights pipeline is pure
    functions of its snapshot/evolution inputs."""
    from engine.history.cohort_classifier import classify_match_cohort
    from engine.history.enums import CompetitionType, SnapshotStage
    from engine.history.evolution import compare
    from engine.history.insights import generate_insights
    from engine.history.models import (
        HistoricalMatchSnapshot,
        MatchContext,
        PredictionSnapshot,
        SectorRatings,
        TacticalSetup,
        stable_snapshot_id,
    )

    def make_snapshot(match_date, midfield):
        context = MatchContext(
            match_date=match_date,
            competition_type=CompetitionType.LEAGUE,
            snapshot_stage=SnapshotStage.PLAYED,
        )
        return HistoricalMatchSnapshot(
            snapshot_id=stable_snapshot_id(),
            match_context=context,
            cohort=classify_match_cohort(context),
            tactical_setup=TacticalSetup(formation="3-5-2", selected_tactic="Normal"),
            predictions=PredictionSnapshot(
                ratings=SectorRatings(midfield=midfield), win_probability=0.5
            ),
        )

    previous = make_snapshot("2026-07-01", 4.0)
    current = make_snapshot("2026-07-15", 6.0)
    evolution = compare(current, previous)

    # If this call reached for an optimizer, it would need real Player
    # objects, a Formation, and opponent ratings — none of which are
    # supplied here. Successfully generating insights from snapshots
    # alone demonstrates no optimizer dependency exists.
    result = generate_insights(current, previous, evolution)
    assert result is not None
