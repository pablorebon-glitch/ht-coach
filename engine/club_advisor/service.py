from __future__ import annotations

from datetime import datetime, timezone

from engine.club_advisor.confidence import ClubConfidenceInputs, classify_confidence
from engine.club_advisor.dimensions import evaluate_project_status
from engine.club_advisor.enums import ClubLimitationType
from engine.club_advisor.models import ClubAdvisorReport
from engine.club_advisor.rule_engine import ClubAdvisorRuleEngine
from engine.club_advisor.validation import ensure_context_valid

_DEFAULT_ENGINE = ClubAdvisorRuleEngine()

# These five are permanent limitations of this sprint's scope -- the Advisor
# has no financial, league, transfer-market, salary-budget or promotion-target
# data source at all, by design (see docs/CLUB_ADVISOR.md "Out of scope").
_ALWAYS_PRESENT_LIMITATIONS = (
    ClubLimitationType.FINANCIAL_DATA_UNAVAILABLE,
    ClubLimitationType.LEAGUE_COMPARISON_UNAVAILABLE,
    ClubLimitationType.TRANSFER_MARKET_UNAVAILABLE,
    ClubLimitationType.SALARY_BUDGET_UNAVAILABLE,
    ClubLimitationType.PROMOTION_TARGET_UNKNOWN,
)


def _detect_limitations(context):
    limitations = list(_ALWAYS_PRESENT_LIMITATIONS)
    if not context.roster_size:
        limitations.append(ClubLimitationType.EMPTY_ROSTER)
    if not context.has_active_training:
        limitations.append(ClubLimitationType.NO_ACTIVE_TRAINING)
    if not context.has_historical_data:
        limitations.append(ClubLimitationType.HISTORICAL_DATA_UNAVAILABLE)
    return tuple(limitations)


def generate_report(context, engine=None) -> ClubAdvisorReport:
    """Pure function: given a ClubAdvisorContext (already built from
    Squad Intelligence reports and Training coverage), returns a
    complete ClubAdvisorReport. No I/O, no Qt, no localization --
    everything user-facing here is a stable key or typed enum."""
    ensure_context_valid(context)
    engine = engine or _DEFAULT_ENGINE

    results = engine.evaluate(context)

    project_status = evaluate_project_status(
        results["training_summary"],
        results["squad_summary"],
        results["depth_summary"],
        context.roster_size,
    )

    limitations = _detect_limitations(context)
    confidence = classify_confidence(
        ClubConfidenceInputs(
            has_roster=bool(context.roster_size),
            has_active_training=context.has_active_training,
            has_squad_reports=bool(context.squad_reports),
            has_historical_data=context.has_historical_data,
        )
    )

    return ClubAdvisorReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        strategy=context.strategy,
        project_status=project_status,
        priorities=results["priorities"],
        strengths=results["strengths"],
        risks=results["risks"],
        training_summary=results["training_summary"],
        squad_summary=results["squad_summary"],
        depth_summary=results["depth_summary"],
        sporting_summary=results["sporting_summary"],
        warnings=results["warnings"],
        confidence=confidence,
        limitations=limitations,
        evidence=(),
    )
