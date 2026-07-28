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
from engine.history.evolution.comparison_models import Trend

IM_MIN_FOR_CONTRIBUTOR = 2
IMPROVED_TRENDS = (Trend.IMPROVEMENT, Trend.MAJOR_IMPROVEMENT)


def _order_evidence(change):
    return InsightEvidence(
        evidence_type=EvidenceType.INDIVIDUAL_ORDER_CHANGE,
        entity_id=change.player_id or change.player_name,
        entity_label=change.player_name,
        previous_value=change.previous_order,
        current_value=change.current_order,
        source_snapshot="both",
        reliability="direct",
    )


class OrderChangedRule(InsightRule):
    rule_id = "order.changed"
    category = InsightCategory.INDIVIDUAL_ORDER
    priority = 40

    def evaluate(self, context):
        changes = context.evolution.lineup.order_changes
        if not changes:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.order.changed.title",
                message_key=(
                    "insight.order.changed.message.single"
                    if len(changes) == 1
                    else "insight.order.changed.message.multiple"
                ),
                message_params={
                    "count": len(changes),
                    "player_name": changes[0].player_name if len(changes) == 1 else "",
                    "previous_order": changes[0].previous_order if len(changes) == 1 else "",
                    "current_order": changes[0].current_order if len(changes) == 1 else "",
                },
                evidence=tuple(_order_evidence(c) for c in changes),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(changes),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class InnerMidfieldersOffensiveContributorRule(InsightRule):
    """The engine's flagship example of the causal-language guardrail:
    several inner midfielders switching to an Offensive order alongside
    an improved midfield rating is a plausible, evidence-backed
    contributor — never asserted as the cause."""

    rule_id = "order.inner_midfielders_offensive_likely_contributor"
    category = InsightCategory.INDIVIDUAL_ORDER
    priority = 85

    def evaluate(self, context):
        midfield = next(
            (s for s in context.evolution.sectors if s.sector == "midfield"), None
        )
        if midfield is None or midfield.trend not in IMPROVED_TRENDS:
            return ()

        offensive_im_changes = [
            change
            for change in context.evolution.lineup.order_changes
            if change.current_position == "INNER_MIDFIELDER"
            and change.current_order.strip().casefold() == "offensive"
            and change.previous_order.strip().casefold() != "offensive"
        ]
        if len(offensive_im_changes) < IM_MIN_FOR_CONTRIBUTOR:
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
        order_evidence = tuple(_order_evidence(c) for c in offensive_im_changes)

        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.POSITIVE,
                relationship=InsightRelationship.LIKELY_CONTRIBUTOR,
                title_key="insight.order.inner_midfielders_offensive_likely_contributor.title",
                message_key="insight.order.inner_midfielders_offensive_likely_contributor.message",
                message_params={"count": len(offensive_im_changes)},
                evidence=(sector_evidence,) + order_evidence,
                affected_sectors=("midfield",),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=False,
                        data_complete=True,
                        deterministic_sector_effect=False,
                        supporting_signal_count=1 + len(offensive_im_changes),
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class WingerOrderChangedRule(InsightRule):
    rule_id = "order.winger_changed"
    category = InsightCategory.INDIVIDUAL_ORDER
    priority = 35

    def evaluate(self, context):
        changes = [
            change
            for change in context.evolution.lineup.order_changes
            if change.current_position == "WINGER"
        ]
        if not changes:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.order.winger_changed.title",
                message_key="insight.order.winger_changed.message",
                message_params={"count": len(changes)},
                evidence=tuple(_order_evidence(c) for c in changes),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(changes),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class ForwardTowardsWingRule(InsightRule):
    rule_id = "order.forward_towards_wing"
    category = InsightCategory.INDIVIDUAL_ORDER
    priority = 35

    def evaluate(self, context):
        changes = [
            change
            for change in context.evolution.lineup.order_changes
            if change.current_position == "FORWARD"
            and change.current_order.strip().casefold() == "towards wing"
        ]
        if not changes:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.order.forward_towards_wing.title",
                message_key="insight.order.forward_towards_wing.message",
                message_params={"count": len(changes)},
                evidence=tuple(_order_evidence(c) for c in changes),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(changes),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class DefenderOrderChangedRule(InsightRule):
    rule_id = "order.defender_changed"
    category = InsightCategory.INDIVIDUAL_ORDER
    priority = 35

    def evaluate(self, context):
        changes = [
            change
            for change in context.evolution.lineup.order_changes
            if change.current_position in ("CENTRAL_DEFENDER", "WING_BACK")
        ]
        if not changes:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.order.defender_changed.title",
                message_key="insight.order.defender_changed.message",
                message_params={"count": len(changes)},
                evidence=tuple(_order_evidence(c) for c in changes),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(changes),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class OrderSideChangedRule(InsightRule):
    """Uses the canonical order-side values exactly as persisted — this
    rule must never apply Formation Board visual mirroring logic."""

    rule_id = "order.order_side_changed"
    category = InsightCategory.INDIVIDUAL_ORDER
    priority = 30

    def evaluate(self, context):
        changes = context.evolution.lineup.order_side_changes
        if not changes:
            return ()
        evidence = tuple(
            InsightEvidence(
                evidence_type=EvidenceType.ORDER_SIDE_CHANGE,
                entity_id=change.player_id or change.player_name,
                entity_label=change.player_name,
                previous_value=change.previous_order_side,
                current_value=change.current_order_side,
                source_snapshot="both",
                reliability="direct",
            )
            for change in changes
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.order.order_side_changed.title",
                message_key="insight.order.order_side_changed.message",
                message_params={"count": len(changes)},
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(changes),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


def default_order_rules() -> tuple:
    return (
        OrderChangedRule(),
        InnerMidfieldersOffensiveContributorRule(),
        WingerOrderChangedRule(),
        ForwardTowardsWingRule(),
        DefenderOrderChangedRule(),
        OrderSideChangedRule(),
    )
