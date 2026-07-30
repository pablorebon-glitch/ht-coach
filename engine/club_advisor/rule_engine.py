from __future__ import annotations

from engine.club_advisor.priorities import generate_priorities
from engine.club_advisor.risks import detect_risks
from engine.club_advisor.strengths import detect_strengths
from engine.club_advisor.summary import (
    build_depth_summary,
    build_sporting_summary,
    build_squad_summary,
    build_training_summary,
)
from engine.club_advisor.warnings import generate_warnings


class ClubAdvisorRuleEngine:
    """Thin, explicit orchestration: build the summaries first (they're
    pure aggregations of already-computed Squad Intelligence / Training
    data), then evaluate priorities/strengths/risks/warnings against
    them. No conflict resolution is needed here -- unlike Squad
    Intelligence's role/status rules, every detector below may fire
    independently and all of its results are kept."""

    def evaluate(self, context):
        training_summary = build_training_summary(context)
        squad_summary = build_squad_summary(context)
        depth_summary = build_depth_summary(context)
        sporting_summary = build_sporting_summary(depth_summary)

        priorities = generate_priorities(context, training_summary, squad_summary, depth_summary)
        strengths = detect_strengths(context, training_summary, squad_summary, depth_summary)
        risks = detect_risks(context, training_summary, squad_summary, depth_summary)
        warnings = generate_warnings(context, training_summary, squad_summary, depth_summary)

        return {
            "training_summary": training_summary,
            "squad_summary": squad_summary,
            "depth_summary": depth_summary,
            "sporting_summary": sporting_summary,
            "priorities": priorities,
            "strengths": strengths,
            "risks": risks,
            "warnings": warnings,
        }
