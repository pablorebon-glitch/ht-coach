from __future__ import annotations

from engine.history.insights.confidence import ConfidenceInputs, classify_confidence
from engine.history.insights.enums import (
    EvidenceType,
    InsightCategory,
    InsightDirection,
    InsightRelationship,
    InsightSeverity,
)
from engine.history.insights.evidence import InsightEvidence
from engine.history.insights.models import HistoricalInsight
from engine.history.insights.rule import InsightRule


class TacticChangedRule(InsightRule):
    rule_id = "tactic.changed"
    category = InsightCategory.TACTIC
    priority = 50

    def evaluate(self, context):
        tactical = context.evolution.tactical
        if not tactical.tactic_changed:
            return ()
        evidence = InsightEvidence(
            evidence_type=EvidenceType.TACTIC_CHANGE,
            entity_id="tactic",
            previous_value=tactical.previous_tactic,
            current_value=tactical.current_tactic,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.tactic.changed.title",
                message_key="insight.tactic.changed.message",
                message_params={
                    "previous": tactical.previous_tactic,
                    "current": tactical.current_tactic,
                },
                evidence=(evidence,),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class TacticLevelChangedRule(InsightRule):
    rule_id = "tactic.level_changed"
    category = InsightCategory.TACTIC
    priority = 40

    def evaluate(self, context):
        tactical = context.evolution.tactical
        if tactical.tactic_level_delta is None or tactical.tactic_level_delta == 0:
            return ()
        direction = (
            InsightDirection.POSITIVE
            if tactical.tactic_level_delta > 0
            else InsightDirection.NEGATIVE
        )
        evidence = InsightEvidence(
            evidence_type=EvidenceType.TACTIC_LEVEL_CHANGE,
            entity_id="tactic_level",
            previous_value=tactical.previous_tactic_level,
            current_value=tactical.current_tactic_level,
            delta=tactical.tactic_level_delta,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=direction,
                relationship=InsightRelationship.OBSERVED,
                title_key=(
                    "insight.tactic.level_improved.title"
                    if direction == InsightDirection.POSITIVE
                    else "insight.tactic.level_declined.title"
                ),
                message_key=(
                    "insight.tactic.level_improved.message"
                    if direction == InsightDirection.POSITIVE
                    else "insight.tactic.level_declined.message"
                ),
                message_params={"delta": tactical.tactic_level_delta},
                evidence=(evidence,),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class AttitudeChangedRule(InsightRule):
    rule_id = "tactic.attitude_changed"
    category = InsightCategory.TACTIC
    priority = 35

    def evaluate(self, context):
        tactical = context.evolution.tactical
        if not tactical.attitude_changed:
            return ()
        evidence = InsightEvidence(
            evidence_type=EvidenceType.ATTITUDE_CHANGE,
            entity_id="attitude",
            previous_value=tactical.previous_attitude,
            current_value=tactical.current_attitude,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.tactic.attitude_changed.title",
                message_key="insight.tactic.attitude_changed.message",
                message_params={
                    "previous": tactical.previous_attitude,
                    "current": tactical.current_attitude,
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
                priority=self.priority,
            ),
        )


class ConfidenceChangedRule(InsightRule):
    rule_id = "tactic.confidence_changed"
    category = InsightCategory.TACTIC
    priority = 25

    def evaluate(self, context):
        tactical = context.evolution.tactical
        if not tactical.confidence_changed:
            return ()
        evidence = InsightEvidence(
            evidence_type=EvidenceType.CONFIDENCE_CHANGE,
            entity_id="confidence",
            previous_value=tactical.previous_confidence,
            current_value=tactical.current_confidence,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.tactic.confidence_changed.title",
                message_key="insight.tactic.confidence_changed.message",
                message_params={
                    "previous": tactical.previous_confidence,
                    "current": tactical.current_confidence,
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
                priority=self.priority,
            ),
        )


class HomeAwayChangedRule(InsightRule):
    """Reads match_context directly: home/away isn't part of the
    Evolution Engine's tactical comparison."""

    rule_id = "tactic.home_away_changed"
    category = InsightCategory.TACTIC
    priority = 20

    def evaluate(self, context):
        previous_home_away = context.previous_snapshot.match_context.home_away
        current_home_away = context.current_snapshot.match_context.home_away
        if previous_home_away == current_home_away:
            return ()
        evidence = InsightEvidence(
            evidence_type=EvidenceType.HOME_AWAY_CHANGE,
            entity_id="home_away",
            previous_value=previous_home_away.value,
            current_value=current_home_away.value,
            source_snapshot="both",
            reliability="direct",
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.tactic.home_away_changed.title",
                message_key="insight.tactic.home_away_changed.message",
                message_params={
                    "previous": previous_home_away.value,
                    "current": current_home_away.value,
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
                priority=self.priority,
            ),
        )


def default_tactical_rules() -> tuple:
    return (
        TacticChangedRule(),
        TacticLevelChangedRule(),
        AttitudeChangedRule(),
        ConfidenceChangedRule(),
        HomeAwayChangedRule(),
    )
