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


def _metric_evidence(evidence_type, metric):
    return InsightEvidence(
        evidence_type=evidence_type,
        entity_id=evidence_type.value,
        previous_value=metric.previous,
        current_value=metric.current,
        delta=metric.delta,
        source_snapshot="both",
        reliability="direct",
    )


class WinProbabilityChangedRule(InsightRule):
    rule_id = "prediction.win_probability_changed"
    category = InsightCategory.PREDICTION
    priority = 45

    def evaluate(self, context):
        metric = context.evolution.prediction.win_probability
        if metric.delta is None or metric.delta == 0:
            return ()
        direction = (
            InsightDirection.POSITIVE if metric.delta > 0 else InsightDirection.NEGATIVE
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=direction,
                relationship=InsightRelationship.OBSERVED,
                title_key=(
                    "insight.prediction.win_probability_increased.title"
                    if direction == InsightDirection.POSITIVE
                    else "insight.prediction.win_probability_decreased.title"
                ),
                message_key=(
                    "insight.prediction.win_probability_increased.message"
                    if direction == InsightDirection.POSITIVE
                    else "insight.prediction.win_probability_decreased.message"
                ),
                message_params={"delta": metric.delta},
                evidence=(
                    _metric_evidence(EvidenceType.WIN_PROBABILITY_CHANGE, metric),
                ),
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


class ExpectedGoalsChangedRule(InsightRule):
    rule_id = "prediction.expected_goals_changed"
    category = InsightCategory.PREDICTION
    priority = 40

    def evaluate(self, context):
        metric = context.evolution.prediction.expected_goals
        if metric.delta is None or metric.delta == 0:
            return ()
        direction = (
            InsightDirection.POSITIVE if metric.delta > 0 else InsightDirection.NEGATIVE
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=direction,
                relationship=InsightRelationship.OBSERVED,
                title_key=(
                    "insight.prediction.expected_goals_improved.title"
                    if direction == InsightDirection.POSITIVE
                    else "insight.prediction.expected_goals_declined.title"
                ),
                message_key=(
                    "insight.prediction.expected_goals_improved.message"
                    if direction == InsightDirection.POSITIVE
                    else "insight.prediction.expected_goals_declined.message"
                ),
                message_params={"delta": metric.delta},
                evidence=(
                    _metric_evidence(EvidenceType.EXPECTED_GOALS_CHANGE, metric),
                ),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=True,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class OpponentExpectedGoalsIncreasedRule(InsightRule):
    rule_id = "prediction.opponent_expected_goals_increased"
    category = InsightCategory.PREDICTION
    priority = 40

    def evaluate(self, context):
        metric = context.evolution.prediction.opponent_expected_goals
        if metric.delta is None or metric.delta <= 0:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEGATIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.prediction.opponent_expected_goals_increased.title",
                message_key="insight.prediction.opponent_expected_goals_increased.message",
                message_params={"delta": metric.delta},
                evidence=(
                    _metric_evidence(
                        EvidenceType.OPPONENT_EXPECTED_GOALS_CHANGE, metric
                    ),
                ),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=True,
                        supporting_signal_count=1,
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class PossessionChangedRule(InsightRule):
    rule_id = "prediction.possession_changed"
    category = InsightCategory.PREDICTION
    priority = 25

    def evaluate(self, context):
        metric = context.evolution.prediction.possession
        if metric.delta is None or metric.delta == 0:
            return ()
        direction = (
            InsightDirection.POSITIVE if metric.delta > 0 else InsightDirection.NEGATIVE
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=direction,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.prediction.possession_changed.title",
                message_key="insight.prediction.possession_changed.message",
                message_params={"delta": metric.delta},
                evidence=(
                    _metric_evidence(EvidenceType.POSSESSION_CHANGE, metric),
                ),
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


def default_prediction_rules() -> tuple:
    return (
        WinProbabilityChangedRule(),
        ExpectedGoalsChangedRule(),
        OpponentExpectedGoalsIncreasedRule(),
        PossessionChangedRule(),
    )
