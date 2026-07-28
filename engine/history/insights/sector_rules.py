from __future__ import annotations

from engine.history.evolution.comparison_metrics import safe_average
from engine.history.evolution.comparison_models import Trend, classify_trend
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

ATTACK_SECTORS = ("left_attack", "central_attack", "right_attack")
DEFENSE_SECTORS = ("left_defense", "central_defense", "right_defense")

IMPROVED_TRENDS = (Trend.IMPROVEMENT, Trend.MAJOR_IMPROVEMENT)
DECLINED_TRENDS = (Trend.DECLINE, Trend.MAJOR_DECLINE)


def _sector(evolution, name):
    return next((s for s in evolution.sectors if s.sector == name), None)


def _sector_evidence(sector):
    return InsightEvidence(
        evidence_type=EvidenceType.SECTOR_DELTA,
        entity_id=sector.sector,
        entity_label=sector.sector,
        previous_value=sector.previous_value,
        current_value=sector.current_value,
        delta=sector.absolute_delta,
        source_snapshot="both",
        reliability="direct",
        affected_sectors=(sector.sector,),
    )


def _sector_confidence(sector) -> tuple:
    data_complete = sector.previous_value is not None and sector.current_value is not None
    return classify_confidence(
        ConfidenceInputs(
            has_required_evidence=data_complete,
            data_complete=data_complete,
            structural_change=True,
            deterministic_sector_effect=True,
            supporting_signal_count=1 if data_complete else 0,
        )
    )


class MidfieldImprovementRule(InsightRule):
    rule_id = "sector.midfield_improvement"
    category = InsightCategory.SECTOR_PERFORMANCE
    priority = 90

    def evaluate(self, context):
        midfield = _sector(context.evolution, "midfield")
        if midfield is None or midfield.trend not in IMPROVED_TRENDS:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.POSITIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.sector.midfield_improvement.title",
                message_key="insight.sector.midfield_improvement.message",
                message_params={"delta": midfield.absolute_delta},
                evidence=(_sector_evidence(midfield),),
                affected_sectors=("midfield",),
                confidence=_sector_confidence(midfield),
                severity=(
                    InsightSeverity.CRITICAL
                    if midfield.trend == Trend.MAJOR_IMPROVEMENT
                    else InsightSeverity.NOTABLE
                ),
                priority=self.priority,
            ),
        )


class MidfieldDeclineRule(InsightRule):
    rule_id = "sector.midfield_decline"
    category = InsightCategory.SECTOR_PERFORMANCE
    priority = 90

    def evaluate(self, context):
        midfield = _sector(context.evolution, "midfield")
        if midfield is None or midfield.trend not in DECLINED_TRENDS:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEGATIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.sector.midfield_decline.title",
                message_key="insight.sector.midfield_decline.message",
                message_params={"delta": midfield.absolute_delta},
                evidence=(_sector_evidence(midfield),),
                affected_sectors=("midfield",),
                confidence=_sector_confidence(midfield),
                severity=(
                    InsightSeverity.CRITICAL
                    if midfield.trend == Trend.MAJOR_DECLINE
                    else InsightSeverity.NOTABLE
                ),
                priority=self.priority,
            ),
        )


class _AggregateSectorRule(InsightRule):
    """Shared logic for attack/defense aggregate improvement/decline
    rules: average the percentage delta across the three directional
    sectors and classify that average with the same thresholds used
    for individual sectors."""

    sectors_group: tuple = ()
    wanted_trends: tuple = ()

    def _aggregate_trend(self, context):
        sectors = [_sector(context.evolution, name) for name in self.sectors_group]
        sectors = [s for s in sectors if s is not None]
        if not sectors:
            return None, ()
        average_pct = safe_average(s.percentage_delta for s in sectors)
        return classify_trend(average_pct), tuple(sectors)

    def _confidence(self, sectors):
        complete = [
            s for s in sectors
            if s.previous_value is not None and s.current_value is not None
        ]
        data_complete = len(complete) == len(sectors) and len(sectors) > 0
        return classify_confidence(
            ConfidenceInputs(
                has_required_evidence=bool(complete),
                data_complete=data_complete,
                structural_change=True,
                deterministic_sector_effect=True,
                supporting_signal_count=len(complete),
            )
        )


class AttackImprovementRule(_AggregateSectorRule):
    rule_id = "sector.attack_improvement"
    category = InsightCategory.SECTOR_PERFORMANCE
    priority = 70
    sectors_group = ATTACK_SECTORS

    def evaluate(self, context):
        trend, sectors = self._aggregate_trend(context)
        if trend not in IMPROVED_TRENDS:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.POSITIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.sector.attack_improvement.title",
                message_key="insight.sector.attack_improvement.message",
                evidence=tuple(_sector_evidence(s) for s in sectors),
                affected_sectors=self.sectors_group,
                confidence=self._confidence(sectors),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class AttackDeclineRule(_AggregateSectorRule):
    rule_id = "sector.attack_decline"
    category = InsightCategory.SECTOR_PERFORMANCE
    priority = 70
    sectors_group = ATTACK_SECTORS

    def evaluate(self, context):
        trend, sectors = self._aggregate_trend(context)
        if trend not in DECLINED_TRENDS:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEGATIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.sector.attack_decline.title",
                message_key="insight.sector.attack_decline.message",
                evidence=tuple(_sector_evidence(s) for s in sectors),
                affected_sectors=self.sectors_group,
                confidence=self._confidence(sectors),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class DefenseImprovementRule(_AggregateSectorRule):
    rule_id = "sector.defense_improvement"
    category = InsightCategory.SECTOR_PERFORMANCE
    priority = 70
    sectors_group = DEFENSE_SECTORS

    def evaluate(self, context):
        trend, sectors = self._aggregate_trend(context)
        if trend not in IMPROVED_TRENDS:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.POSITIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.sector.defense_improvement.title",
                message_key="insight.sector.defense_improvement.message",
                evidence=tuple(_sector_evidence(s) for s in sectors),
                affected_sectors=self.sectors_group,
                confidence=self._confidence(sectors),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class DefenseDeclineRule(_AggregateSectorRule):
    rule_id = "sector.defense_decline"
    category = InsightCategory.SECTOR_PERFORMANCE
    priority = 70
    sectors_group = DEFENSE_SECTORS

    def evaluate(self, context):
        trend, sectors = self._aggregate_trend(context)
        if trend not in DECLINED_TRENDS:
            return ()
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEGATIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.sector.defense_decline.title",
                message_key="insight.sector.defense_decline.message",
                evidence=tuple(_sector_evidence(s) for s in sectors),
                affected_sectors=self.sectors_group,
                confidence=self._confidence(sectors),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )


class BroadImprovementRule(InsightRule):
    rule_id = "sector.broad_improvement"
    category = InsightCategory.OVERALL
    priority = 95

    def evaluate(self, context):
        overall = context.evolution.overall
        total = len(context.evolution.sectors)
        if total == 0 or overall.improved_sector_count <= total // 2:
            return ()
        if overall.improved_sector_count <= overall.declined_sector_count:
            return ()
        improved_sectors = tuple(
            s.sector for s in context.evolution.sectors if s.trend in IMPROVED_TRENDS
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.POSITIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.overall.broad_improvement.title",
                message_key="insight.overall.broad_improvement.message",
                message_params={"count": overall.improved_sector_count, "total": total},
                evidence=tuple(
                    _sector_evidence(s)
                    for s in context.evolution.sectors
                    if s.trend in IMPROVED_TRENDS
                ),
                affected_sectors=improved_sectors,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=True,
                        supporting_signal_count=overall.improved_sector_count,
                    )
                ),
                severity=InsightSeverity.CRITICAL,
                priority=self.priority,
            ),
        )


class BroadDeclineRule(InsightRule):
    rule_id = "sector.broad_decline"
    category = InsightCategory.OVERALL
    priority = 95

    def evaluate(self, context):
        overall = context.evolution.overall
        total = len(context.evolution.sectors)
        if total == 0 or overall.declined_sector_count <= total // 2:
            return ()
        if overall.declined_sector_count <= overall.improved_sector_count:
            return ()
        declined_sectors = tuple(
            s.sector for s in context.evolution.sectors if s.trend in DECLINED_TRENDS
        )
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEGATIVE,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.overall.broad_decline.title",
                message_key="insight.overall.broad_decline.message",
                message_params={"count": overall.declined_sector_count, "total": total},
                evidence=tuple(
                    _sector_evidence(s)
                    for s in context.evolution.sectors
                    if s.trend in DECLINED_TRENDS
                ),
                affected_sectors=declined_sectors,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=True,
                        supporting_signal_count=overall.declined_sector_count,
                    )
                ),
                severity=InsightSeverity.CRITICAL,
                priority=self.priority,
            ),
        )


class AttackDefenseTradeoffRule(InsightRule):
    rule_id = "sector.attack_defense_tradeoff"
    category = InsightCategory.OVERALL
    priority = 80

    def evaluate(self, context):
        attack_trend, attack_sectors = self._trend(context, ATTACK_SECTORS)
        defense_trend, defense_sectors = self._trend(context, DEFENSE_SECTORS)
        if attack_trend is None or defense_trend is None:
            return ()

        tradeoff = (
            attack_trend in IMPROVED_TRENDS and defense_trend in DECLINED_TRENDS
        ) or (
            attack_trend in DECLINED_TRENDS and defense_trend in IMPROVED_TRENDS
        )
        if not tradeoff:
            return ()

        sectors = attack_sectors + defense_sectors
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.MIXED,
                relationship=InsightRelationship.OBSERVED,
                title_key="insight.overall.attack_defense_tradeoff.title",
                message_key="insight.overall.attack_defense_tradeoff.message",
                evidence=tuple(_sector_evidence(s) for s in sectors),
                affected_sectors=ATTACK_SECTORS + DEFENSE_SECTORS,
                confidence=classify_confidence(
                    ConfidenceInputs(
                        structural_change=True,
                        data_complete=True,
                        deterministic_sector_effect=True,
                        supporting_signal_count=len(sectors),
                    )
                ),
                severity=InsightSeverity.NOTABLE,
                priority=self.priority,
            ),
        )

    @staticmethod
    def _trend(context, group):
        sectors = [_sector(context.evolution, name) for name in group]
        sectors = [s for s in sectors if s is not None]
        if not sectors:
            return None, ()
        average_pct = safe_average(s.percentage_delta for s in sectors)
        return classify_trend(average_pct), tuple(sectors)


def default_sector_rules() -> tuple:
    return (
        MidfieldImprovementRule(),
        MidfieldDeclineRule(),
        AttackImprovementRule(),
        AttackDeclineRule(),
        DefenseImprovementRule(),
        DefenseDeclineRule(),
        BroadImprovementRule(),
        BroadDeclineRule(),
        AttackDefenseTradeoffRule(),
    )
