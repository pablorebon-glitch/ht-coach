from __future__ import annotations

import re

from engine.history.insights.confidence import ConfidenceInputs, classify_confidence
from engine.history.insights.enums import (
    EvidenceType,
    InsightCategory,
    InsightConfidence,
    InsightDirection,
    InsightRelationship,
    InsightSeverity,
)
from engine.history.insights.evidence import InsightEvidence
from engine.history.insights.models import HistoricalInsight
from engine.history.insights.rule import InsightRule
from engine.history.evolution.comparison_models import Trend

_FORMATION_PATTERN = re.compile(r"^(\d+)-(\d+)-(\d+)$")

IMPROVED_TRENDS = (Trend.IMPROVEMENT, Trend.MAJOR_IMPROVEMENT)


def parse_formation_counts(formation: str):
    """Parses a "D-M-F" formation label (e.g. "3-5-2") into
    (defenders, midfielders, forwards). Returns None for anything that
    doesn't match this app's formation-naming convention, rather than
    guessing."""
    if not formation:
        return None
    match = _FORMATION_PATTERN.match(formation.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


class FormationChangedRule(InsightRule):
    rule_id = "formation.changed"
    category = InsightCategory.FORMATION
    priority = 60

    def evaluate(self, context):
        formation = context.evolution.formation
        if not formation.changed:
            return ()
        evidence = InsightEvidence(
            evidence_type=EvidenceType.FORMATION_CHANGE,
            entity_id="formation",
            entity_label="formation",
            previous_value=formation.previous_formation,
            current_value=formation.current_formation,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.formation.changed.title",
                message_key="insight.formation.changed.message",
                message_params={
                    "previous": formation.previous_formation,
                    "current": formation.current_formation,
                },
                evidence=(evidence,),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=False,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class _SlotCountRule(InsightRule):
    slot_index: int = 0
    evidence_type = None

    def evaluate(self, context):
        formation = context.evolution.formation
        previous_counts = parse_formation_counts(formation.previous_formation)
        current_counts = parse_formation_counts(formation.current_formation)
        if previous_counts is None or current_counts is None:
            return ()
        previous_count = previous_counts[self.slot_index]
        current_count = current_counts[self.slot_index]
        if previous_count == current_count:
            return ()
        evidence = InsightEvidence(
            evidence_type=self.evidence_type,
            entity_id=self.rule_id,
            previous_value=previous_count,
            current_value=current_count,
            delta=current_count - previous_count,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=InsightCategory.FORMATION,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key=f"insight.{self.rule_id}.title",
                message_key=f"insight.{self.rule_id}.message",
                message_params={
                    "previous": previous_count,
                    "current": current_count,
                },
                evidence=(evidence,),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=55,
            ),
        )


class MidfielderCountChangedRule(_SlotCountRule):
    rule_id = "formation.midfielder_count_changed"
    slot_index = 1
    evidence_type = EvidenceType.MIDFIELDER_COUNT


class DefenderCountChangedRule(_SlotCountRule):
    rule_id = "formation.defender_count_changed"
    slot_index = 0
    evidence_type = EvidenceType.DEFENDER_COUNT


class ForwardCountChangedRule(_SlotCountRule):
    rule_id = "formation.forward_count_changed"
    slot_index = 2
    evidence_type = EvidenceType.FORWARD_COUNT


class SameFormationDifferentRatingsRule(InsightRule):
    """Same formation, materially different overall ratings: worth
    flagging as its own observation, since a naive reader might assume
    'nothing changed' just because the formation string is identical."""

    rule_id = "formation.same_formation_different_ratings"
    category = InsightCategory.FORMATION
    priority = 50

    def evaluate(self, context):
        formation = context.evolution.formation
        if formation.changed:
            return ()
        overall = context.evolution.overall
        if overall.average_sector_delta is None:
            return ()
        if overall.overall_trend not in (
            Trend.MAJOR_IMPROVEMENT,
            Trend.MAJOR_DECLINE,
        ):
            return ()
        evidence = InsightEvidence(
            evidence_type=EvidenceType.SECTOR_DELTA,
            entity_id="overall",
            previous_value=None,
            current_value=None,
            delta=overall.average_sector_delta,
            source_snapshot="both",
            reliability="direct",
        )
        direction = (
            InsightDirection.POSITIVE
            if overall.overall_trend == Trend.MAJOR_IMPROVEMENT
            else InsightDirection.NEGATIVE
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=direction,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.formation.same_formation_different_ratings.title",
                message_key="insight.formation.same_formation_different_ratings.message",
                message_params={"formation": formation.current_formation},
                evidence=(evidence,),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=True,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class FormationLinkedMidfieldContributorRule(InsightRule):
    """Demonstrates the causal-language guardrail: an added midfield
    slot alongside an improved midfield rating is a *plausible*
    contributor, not a proven cause — hence LIKELY_CONTRIBUTOR with
    MEDIUM confidence rather than an assertion."""

    rule_id = "formation.midfield_slot_added_likely_contributor"
    category = InsightCategory.FORMATION
    priority = 65

    def evaluate(self, context):
        midfield = next(
            (s for s in context.evolution.sectors if s.sector == "midfield"), None
        )
        if midfield is None or midfield.trend not in IMPROVED_TRENDS:
            return ()

        formation = context.evolution.formation
        previous_counts = parse_formation_counts(formation.previous_formation)
        current_counts = parse_formation_counts(formation.current_formation)
        if previous_counts is None or current_counts is None:
            return ()
        if current_counts[1] <= previous_counts[1]:
            return ()

        sector_evidence = InsightEvidence(
            evidence_type=EvidenceType.SECTOR_DELTA,
            entity_id="midfield",
            previous_value=midfield.previous_value,
            current_value=midfield.current_value,
            delta=midfield.absolute_delta,
            source_snapshot="both",
            reliability="direct",
            affected_sectors=("midfield",),
        )
        slot_evidence = InsightEvidence(
            evidence_type=EvidenceType.MIDFIELDER_COUNT,
            entity_id="midfielder_count",
            previous_value=previous_counts[1],
            current_value=current_counts[1],
            delta=current_counts[1] - previous_counts[1],
            source_snapshot="both",
            reliability="indirect",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.POSITIVE,
                relationship=InsightRelationship.LIKELY_CONTRIBUTOR,
                title_key="insight.formation.midfield_slot_added_likely_contributor.title",
                message_key="insight.formation.midfield_slot_added_likely_contributor.message",
                message_params={
                    "previous_slots": previous_counts[1],
                    "current_slots": current_counts[1],
                },
                evidence=(sector_evidence, slot_evidence),
                affected_sectors=("midfield",),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=False,
                        data_complete=True,
                        deterministic_sector_effect=False,
                        supporting_signal_count=2,
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


def default_formation_rules() -> tuple:
    return (
        FormationChangedRule(),
        MidfielderCountChangedRule(),
        DefenderCountChangedRule(),
        ForwardCountChangedRule(),
        SameFormationDifferentRatingsRule(),
        FormationLinkedMidfieldContributorRule(),
    )
