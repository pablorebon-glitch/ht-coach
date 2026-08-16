from engine.club_advisor.context import ClubAdvisorContext
from engine.club_advisor.enums import ClubWarningType, DepthStatus
from engine.club_advisor.summary import build_depth_summary
from engine.club_advisor.warnings import generate_warnings
from engine.club_advisor.models import TrainingSummary, SquadSummary
from engine.squad_intelligence.context import SquadIntelligenceContext


def make_context(positional_depth=None, temporary_positional_depth=None):
    squad_context = SquadIntelligenceContext(
        roster_size=sum((positional_depth or {}).values()),
        positional_depth=positional_depth or {},
        temporary_positional_depth=temporary_positional_depth or {},
    )
    return ClubAdvisorContext(squad_context=squad_context)


def test_temporary_depth_defaults_to_structural_when_not_set():
    squad_context = SquadIntelligenceContext(positional_depth={"GOALKEEPER": 2})
    assert squad_context.temporary_depth_at("GOALKEEPER") == 2


def test_temporary_depth_can_differ_from_structural():
    squad_context = SquadIntelligenceContext(
        positional_depth={"WING_BACK": 5},
        temporary_positional_depth={"WING_BACK": 4},
    )
    assert squad_context.depth_at("WING_BACK") == 5
    assert squad_context.temporary_depth_at("WING_BACK") == 4


def test_depth_summary_carries_both_structural_and_temporary_counts():
    context = make_context(
        positional_depth={"WING_BACK": 5},
        temporary_positional_depth={"WING_BACK": 4},
    )
    depth_summary = build_depth_summary(context)
    entry = next(item for item in depth_summary.positions if item.position == "WING_BACK")
    assert entry.player_count == 5
    assert entry.temporary_count == 4
    assert entry.has_reduced_temporary_availability is True


def test_structural_status_unaffected_by_temporary_reduction():
    """A short-term injury must not change the *structural* depth
    status -- only a separate temporary_status field reflects it."""
    context = make_context(
        positional_depth={"WING_BACK": 5},
        temporary_positional_depth={"WING_BACK": 1},
    )
    depth_summary = build_depth_summary(context)
    entry = next(item for item in depth_summary.positions if item.position == "WING_BACK")
    assert entry.status == DepthStatus.EXCESS_PLAYERS.value  # structural: still 5, unaffected
    assert entry.temporary_status == DepthStatus.NO_REPLACEMENT.value  # temporary: only 1 available


def test_no_reduction_produces_no_warning():
    context = make_context(
        positional_depth={"CENTRAL_DEFENDER": 3},
        temporary_positional_depth={"CENTRAL_DEFENDER": 3},
    )
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, TrainingSummary(), SquadSummary(), depth_summary)
    assert ClubWarningType.REDUCED_TEMPORARY_AVAILABILITY not in [w.warning_type for w in warnings]


def test_reduction_produces_a_distinct_warning_with_evidence():
    context = make_context(
        positional_depth={"WING_BACK": 5},
        temporary_positional_depth={"WING_BACK": 4},
    )
    depth_summary = build_depth_summary(context)
    warnings = generate_warnings(context, TrainingSummary(), SquadSummary(), depth_summary)
    warning = next(
        w for w in warnings if w.warning_type == ClubWarningType.REDUCED_TEMPORARY_AVAILABILITY
    )
    assert warning.reason_params["structural"] == 5
    assert warning.reason_params["available"] == 4
    assert warning.evidence


def test_reference_example_defender_injured_four_weeks_still_has_structural_depth():
    """The sprint's own worked example: an injured defender does not
    mean "no central defender depth" if the club still owns enough
    players structurally."""
    context = make_context(
        positional_depth={"CENTRAL_DEFENDER": 3},
        temporary_positional_depth={"CENTRAL_DEFENDER": 2},
    )
    depth_summary = build_depth_summary(context)
    entry = next(item for item in depth_summary.positions if item.position == "CENTRAL_DEFENDER")
    assert entry.status != DepthStatus.NO_REPLACEMENT.value  # structural depth: adequate
    assert entry.has_reduced_temporary_availability  # temporary availability: reduced
