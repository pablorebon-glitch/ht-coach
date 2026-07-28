from __future__ import annotations

from engine.history.evolution.comparison_engine import _player_key
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

MULTIPLE_CHANGE_THRESHOLD = 3
STABLE_CORE_MINIMUM = 9


class PlayerAddedRule(InsightRule):
    rule_id = "lineup.player_added"
    category = InsightCategory.LINEUP
    priority = 55

    def evaluate(self, context):
        added = context.evolution.lineup.players_added
        if not added:
            return ()
        evidence = tuple(
            InsightEvidence(
                evidence_type=EvidenceType.PLAYER_ADDED,
                entity_id=change.player_id or change.player_name,
                entity_label=change.player_name,
                current_value=change.current_position,
                source_snapshot="current",
                reliability="direct",
            )
            for change in added
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.lineup.player_added.title",
                message_key=(
                    "insight.lineup.player_added.message.single"
                    if len(added) == 1
                    else "insight.lineup.player_added.message.multiple"
                ),
                message_params={
                    "count": len(added),
                    "player_name": added[0].player_name if len(added) == 1 else "",
                },
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(added),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class PlayerRemovedRule(InsightRule):
    rule_id = "lineup.player_removed"
    category = InsightCategory.LINEUP
    priority = 55

    def evaluate(self, context):
        removed = context.evolution.lineup.players_removed
        if not removed:
            return ()
        evidence = tuple(
            InsightEvidence(
                evidence_type=EvidenceType.PLAYER_REMOVED,
                entity_id=change.player_id or change.player_name,
                entity_label=change.player_name,
                previous_value=change.previous_position,
                source_snapshot="previous",
                reliability="direct",
            )
            for change in removed
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.lineup.player_removed.title",
                message_key=(
                    "insight.lineup.player_removed.message.single"
                    if len(removed) == 1
                    else "insight.lineup.player_removed.message.multiple"
                ),
                message_params={
                    "count": len(removed),
                    "player_name": removed[0].player_name if len(removed) == 1 else "",
                },
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(removed),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


class MultipleStarterChangesRule(InsightRule):
    rule_id = "lineup.multiple_starter_changes"
    category = InsightCategory.LINEUP
    priority = 60

    def evaluate(self, context):
        lineup = context.evolution.lineup
        turnover = len(lineup.players_added) + len(lineup.players_removed)
        if turnover < MULTIPLE_CHANGE_THRESHOLD:
            return ()
        evidence = tuple(
            InsightEvidence(
                evidence_type=(
                    EvidenceType.PLAYER_ADDED
                    if change.status.value == "added"
                    else EvidenceType.PLAYER_REMOVED
                ),
                entity_id=change.player_id or change.player_name,
                entity_label=change.player_name,
                source_snapshot="both",
                reliability="direct",
            )
            for change in (lineup.players_added + lineup.players_removed)
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.lineup.multiple_starter_changes.title",
                message_key="insight.lineup.multiple_starter_changes.message",
                message_params={"count": turnover},
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=turnover,
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class SameCoreLineupRetainedRule(InsightRule):
    rule_id = "lineup.same_core_retained"
    category = InsightCategory.LINEUP
    priority = 30

    def evaluate(self, context):
        lineup = context.evolution.lineup
        kept = len(lineup.players_kept)
        if kept < STABLE_CORE_MINIMUM:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.lineup.same_core_retained.title",
                message_key="insight.lineup.same_core_retained.message",
                message_params={"count": kept},
                evidence=(
                    InsightEvidence(
                        evidence_type=EvidenceType.PLAYER_POSITION_CHANGE,
                        entity_id="core_lineup",
                        current_value=kept,
                        source_snapshot="both",
                        reliability="direct",
                    ),
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


class PlayerPositionChangedRule(InsightRule):
    rule_id = "lineup.player_position_changed"
    category = InsightCategory.LINEUP
    priority = 45

    def evaluate(self, context):
        changes = context.evolution.lineup.position_changes
        if not changes:
            return ()
        evidence = tuple(
            InsightEvidence(
                evidence_type=EvidenceType.PLAYER_POSITION_CHANGE,
                entity_id=change.player_id or change.player_name,
                entity_label=change.player_name,
                previous_value=change.previous_position,
                current_value=change.current_position,
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
                title_key="insight.lineup.player_position_changed.title",
                message_key=(
                    "insight.lineup.player_position_changed.message.single"
                    if len(changes) == 1
                    else "insight.lineup.player_position_changed.message.multiple"
                ),
                message_params={
                    "count": len(changes),
                    "player_name": changes[0].player_name if len(changes) == 1 else "",
                    "previous_position": (
                        changes[0].previous_position if len(changes) == 1 else ""
                    ),
                    "current_position": (
                        changes[0].current_position if len(changes) == 1 else ""
                    ),
                },
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


class PlayerSideChangedRule(InsightRule):
    """The evolution engine (Alpha 0.5.8.3) intentionally does not track
    field `side` changes, only position/order/order-side/number — so
    this rule reads both snapshots' lineups directly rather than
    extending evolution's output."""

    rule_id = "lineup.player_side_changed"
    category = InsightCategory.LINEUP
    priority = 45

    def evaluate(self, context):
        previous_by_key = {
            _player_key(entry): entry
            for entry in (context.previous_snapshot.lineup or ())
        }
        current_by_key = {
            _player_key(entry): entry
            for entry in (context.current_snapshot.lineup or ())
        }

        changed = []
        for key, current_entry in current_by_key.items():
            previous_entry = previous_by_key.get(key)
            if previous_entry is None:
                continue
            if previous_entry.side != current_entry.side:
                changed.append((previous_entry, current_entry))

        if not changed:
            return ()

        evidence = tuple(
            InsightEvidence(
                evidence_type=EvidenceType.PLAYER_POSITION_CHANGE,
                entity_id=current.player_id or current.player_name,
                entity_label=current.player_name,
                previous_value=previous.side,
                current_value=current.side,
                source_snapshot="both",
                reliability="direct",
            )
            for previous, current in changed
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.lineup.player_side_changed.title",
                message_key=(
                    "insight.lineup.player_side_changed.message.single"
                    if len(changed) == 1
                    else "insight.lineup.player_side_changed.message.multiple"
                ),
                message_params={
                    "count": len(changed),
                    "player_name": changed[0][1].player_name if len(changed) == 1 else "",
                    "previous_side": changed[0][0].side if len(changed) == 1 else "",
                    "current_side": changed[0][1].side if len(changed) == 1 else "",
                },
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        supporting_signal_count=len(changed),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


def default_lineup_rules() -> tuple:
    return (
        PlayerAddedRule(),
        PlayerRemovedRule(),
        MultipleStarterChangesRule(),
        SameCoreLineupRetainedRule(),
        PlayerPositionChangedRule(),
        PlayerSideChangedRule(),
    )
