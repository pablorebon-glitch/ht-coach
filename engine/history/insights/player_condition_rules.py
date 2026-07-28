from __future__ import annotations

from dataclasses import fields

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


def _matched_entries(context):
    previous_by_key = {
        _player_key(entry): entry for entry in (context.previous_snapshot.lineup or ())
    }
    current_by_key = {
        _player_key(entry): entry for entry in (context.current_snapshot.lineup or ())
    }
    matched = []
    for key, current_entry in current_by_key.items():
        previous_entry = previous_by_key.get(key)
        if previous_entry is not None:
            matched.append((previous_entry, current_entry))
    return matched


def _attribute_deltas(matched, attribute):
    """[(previous_entry, current_entry, delta), ...] for players where
    both snapshots have a non-None value for `attribute`."""
    deltas = []
    for previous_entry, current_entry in matched:
        previous_value = getattr(previous_entry, attribute, None)
        current_value = getattr(current_entry, attribute, None)
        if previous_value is None or current_value is None:
            continue
        delta = current_value - previous_value
        if delta != 0:
            deltas.append((previous_entry, current_entry, delta))
    return deltas


class _DirectionalAttributeRule(InsightRule):
    """Shared logic for a player-attribute rule that fires in an
    'increased' or 'decreased' direction depending on the net change
    across the matched lineup."""

    attribute: str = ""
    evidence_type = None
    wants_increase: bool = True

    def evaluate(self, context):
        matched = _matched_entries(context)
        deltas = _attribute_deltas(matched, self.attribute)
        if not deltas:
            return ()

        positive = [item for item in deltas if item[2] > 0]
        negative = [item for item in deltas if item[2] < 0]
        if self.wants_increase:
            if len(positive) <= len(negative) or not positive:
                return ()
            relevant = positive
        else:
            if len(negative) <= len(positive) or not negative:
                return ()
            relevant = negative

        evidence = tuple(
            InsightEvidence(
                evidence_type=self.evidence_type,
                entity_id=current.player_id or current.player_name,
                entity_label=current.player_name,
                previous_value=getattr(previous, self.attribute),
                current_value=getattr(current, self.attribute),
                delta=delta,
                source_snapshot="both",
                reliability="direct",
            )
            for previous, current, delta in relevant
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=(
                    InsightDirection.POSITIVE
                    if self.wants_increase
                    else InsightDirection.NEGATIVE
                ),
                relationship=InsightRelationship.OBSERVED,
                title_key=f"insight.{self.rule_id}.title",
                message_key=(
                    f"insight.{self.rule_id}.message.single"
                    if len(relevant) == 1
                    else f"insight.{self.rule_id}.message.multiple"
                ),
                message_params={
                    "count": len(relevant),
                    "player_name": relevant[0][1].player_name if len(relevant) == 1 else "",
                },
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=False,
                        data_complete=True,
                        supporting_signal_count=len(relevant),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=25,
            ),
        )


class FormIncreasedRule(_DirectionalAttributeRule):
    rule_id = "player_condition.form_increased"
    category = InsightCategory.PLAYER_CONDITION
    attribute = "form"
    evidence_type = EvidenceType.PLAYER_FORM_CHANGE
    wants_increase = True


class FormDecreasedRule(_DirectionalAttributeRule):
    rule_id = "player_condition.form_decreased"
    category = InsightCategory.PLAYER_CONDITION
    attribute = "form"
    evidence_type = EvidenceType.PLAYER_FORM_CHANGE
    wants_increase = False


class StaminaIncreasedRule(_DirectionalAttributeRule):
    rule_id = "player_condition.stamina_increased"
    category = InsightCategory.PLAYER_CONDITION
    attribute = "stamina"
    evidence_type = EvidenceType.PLAYER_STAMINA_CHANGE
    wants_increase = True


class StaminaDecreasedRule(_DirectionalAttributeRule):
    rule_id = "player_condition.stamina_decreased"
    category = InsightCategory.PLAYER_CONDITION
    attribute = "stamina"
    evidence_type = EvidenceType.PLAYER_STAMINA_CHANGE
    wants_increase = False


class ExperienceChangedRule(InsightRule):
    rule_id = "player_condition.experience_changed"
    category = InsightCategory.PLAYER_CONDITION
    priority = 20

    def evaluate(self, context):
        matched = _matched_entries(context)
        deltas = _attribute_deltas(matched, "experience")
        if not deltas:
            return ()
        evidence = tuple(
            InsightEvidence(
                evidence_type=EvidenceType.PLAYER_EXPERIENCE_CHANGE,
                entity_id=current.player_id or current.player_name,
                entity_label=current.player_name,
                previous_value=previous.experience,
                current_value=current.experience,
                delta=delta,
                source_snapshot="both",
                reliability="direct",
            )
            for previous, current, delta in deltas
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.player_condition.experience_changed.title",
                message_key="insight.player_condition.experience_changed.message",
                message_params={"count": len(deltas)},
                evidence=evidence,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=False,
                        data_complete=True,
                        supporting_signal_count=len(deltas),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


_SKILL_FIELDS = (
    "goalkeeper",
    "defending",
    "playmaking",
    "winger",
    "passing",
    "scoring",
    "set_pieces",
)


class SkillChangedRule(InsightRule):
    """Reports that skills changed without ever claiming training (or
    anything else) as the cause — a future Training Impact Engine may
    establish that relationship; this rule never does."""

    rule_id = "player_condition.skill_changed"
    category = InsightCategory.PLAYER_CONDITION
    priority = 20

    def evaluate(self, context):
        matched = _matched_entries(context)
        evidence = []
        players_changed = set()
        for previous, current in matched:
            previous_skills = previous.skills
            current_skills = current.skills
            if previous_skills is None or current_skills is None:
                continue
            for field_name in _SKILL_FIELDS:
                previous_value = getattr(previous_skills, field_name, None)
                current_value = getattr(current_skills, field_name, None)
                if previous_value is None or current_value is None:
                    continue
                if previous_value != current_value:
                    players_changed.add(current.player_id or current.player_name)
                    evidence.append(
                        InsightEvidence(
                            evidence_type=EvidenceType.PLAYER_SKILL_CHANGE,
                            entity_id=current.player_id or current.player_name,
                            entity_label=f"{current.player_name}:{field_name}",
                            previous_value=previous_value,
                            current_value=current_value,
                            delta=current_value - previous_value,
                            source_snapshot="both",
                            reliability="direct",
                        )
                    )
        if not evidence:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.player_condition.skill_changed.title",
                message_key="insight.player_condition.skill_changed.message",
                message_params={"count": len(players_changed)},
                evidence=tuple(evidence),
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=False,
                        data_complete=True,
                        supporting_signal_count=len(evidence),
                    )
                ),
                severity=InsightSeverity.MINOR,
                priority=self.priority,
            ),
        )


def default_player_condition_rules() -> tuple:
    return (
        FormIncreasedRule(),
        FormDecreasedRule(),
        StaminaIncreasedRule(),
        StaminaDecreasedRule(),
        ExperienceChangedRule(),
        SkillChangedRule(),
    )
