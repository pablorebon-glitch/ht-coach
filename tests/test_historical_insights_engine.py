import pytest

from engine.history.cohort_classifier import classify_match_cohort
from engine.history.enums import CompetitionType, HomeAway, SnapshotStage, TeamType
from engine.history.evolution import compare
from engine.history.insights import (
    InsightContext,
    InsightRuleEngine,
    generate_insights,
)
from engine.history.insights.confidence import ConfidenceInputs, classify_confidence
from engine.history.insights.enums import (
    InsightCategory,
    InsightConfidence,
    InsightDirection,
    InsightRelationship,
)
from engine.history.insights.formation_rules import parse_formation_counts
from engine.history.insights.models import HistoricalInsight
from engine.history.insights.rule import InsightRule
from engine.history.insights.summary_engine import build_executive_summary
from engine.history.insights.validation import InsightGenerationError
from engine.history.models import (
    HistoricalLineupEntry,
    HistoricalMatchSnapshot,
    HistoricalPlayerSkills,
    MatchContext,
    OpponentReference,
    PredictionSnapshot,
    SectorRatings,
    TacticalSetup,
    stable_snapshot_id,
)


def entry(
    name,
    position="INNER_MIDFIELDER",
    side="CENTER",
    order="Normal",
    order_side="",
    number=1,
    player_id=None,
    form=None,
    stamina=None,
    experience=None,
    skills=None,
):
    return HistoricalLineupEntry(
        player_id=player_id if player_id is not None else f"id-{name}",
        player_name=name,
        number=number,
        position=position,
        side=side,
        individual_order=order,
        order_side=order_side,
        form=form,
        stamina=stamina,
        experience=experience,
        skills=skills if skills is not None else HistoricalPlayerSkills(),
    )


def make_ratings(**overrides):
    base = dict(
        midfield=5.0,
        right_defense=4.0,
        central_defense=4.0,
        left_defense=4.0,
        right_attack=3.0,
        central_attack=3.0,
        left_attack=3.0,
    )
    base.update(overrides)
    return SectorRatings(**base)


def make_snapshot(
    match_date="2026-07-01",
    formation="3-5-2",
    tactic="Normal",
    tactic_level=5.0,
    attitude="Normal",
    confidence="High",
    ratings=None,
    lineup=None,
    home_away=HomeAway.HOME,
    win_probability=0.5,
    expected_goals=1.5,
    opponent_expected_goals=1.0,
    possession=50.0,
    competition_type=CompetitionType.LEAGUE,
):
    context = MatchContext(
        match_date=match_date,
        competition_type=competition_type,
        team_type=TeamType.FIRST_TEAM,
        snapshot_stage=SnapshotStage.PLAYED,
        home_away=home_away,
        opponent=OpponentReference(opponent_name="Rival FC"),
    )
    return HistoricalMatchSnapshot(
        snapshot_id=stable_snapshot_id(),
        match_context=context,
        cohort=classify_match_cohort(context),
        tactical_setup=TacticalSetup(
            formation=formation,
            selected_tactic=tactic,
            tactic_level=tactic_level,
            team_attitude=attitude,
            confidence=confidence,
        ),
        predictions=PredictionSnapshot(
            ratings=ratings if ratings is not None else make_ratings(),
            win_probability=win_probability,
            expected_goals=expected_goals,
            opponent_expected_goals=opponent_expected_goals,
            possession=possession,
        ),
        lineup=tuple(lineup) if lineup is not None else (
            entry("Alice", number=1),
            entry("Bob", number=2),
        ),
    )


def build_context(current, previous):
    evolution = compare(current, previous)
    return InsightContext(
        current_snapshot=current, previous_snapshot=previous, evolution=evolution
    )


# --------------------------------------------------------------------------
# Confidence policy
# --------------------------------------------------------------------------

def test_confidence_high_requires_all_four_signals():
    inputs = ConfidenceInputs(
        structural_change=True,
        data_complete=True,
        deterministic_sector_effect=True,
        contradictory_evidence=False,
    )
    assert classify_confidence(inputs) == InsightConfidence.HIGH


def test_confidence_medium_from_supporting_signals():
    inputs = ConfidenceInputs(
        structural_change=False,
        data_complete=True,
        supporting_signal_count=2,
    )
    assert classify_confidence(inputs) == InsightConfidence.MEDIUM


def test_confidence_low_from_single_indirect_signal():
    inputs = ConfidenceInputs(
        structural_change=False,
        data_complete=False,
        supporting_signal_count=1,
    )
    assert classify_confidence(inputs) == InsightConfidence.LOW


def test_confidence_insufficient_data_when_evidence_missing():
    inputs = ConfidenceInputs(has_required_evidence=False)
    assert classify_confidence(inputs) == InsightConfidence.INSUFFICIENT_DATA


def test_confidence_insufficient_data_when_scales_incompatible():
    inputs = ConfidenceInputs(scales_compatible=False, supporting_signal_count=5)
    assert classify_confidence(inputs) == InsightConfidence.INSUFFICIENT_DATA


def test_confidence_contradictory_evidence_blocks_high():
    inputs = ConfidenceInputs(
        structural_change=True,
        data_complete=True,
        deterministic_sector_effect=True,
        contradictory_evidence=True,
    )
    assert classify_confidence(inputs) != InsightConfidence.HIGH


def test_confidence_zero_signals_is_insufficient_data():
    assert classify_confidence(ConfidenceInputs(supporting_signal_count=0)) == (
        InsightConfidence.INSUFFICIENT_DATA
    )


# --------------------------------------------------------------------------
# HistoricalInsight model guardrails
# --------------------------------------------------------------------------

def test_insight_without_evidence_must_be_insufficient_data():
    with pytest.raises(ValueError):
        HistoricalInsight(
            rule_id="x",
            category=InsightCategory.SECTOR_PERFORMANCE,
            direction=InsightDirection.POSITIVE,
            relationship=InsightRelationship.OBSERVED,
            title_key="t",
            message_key="m",
            confidence=InsightConfidence.HIGH,
        )


def test_insight_without_evidence_allowed_as_insufficient_data():
    insight = HistoricalInsight(
        rule_id="x",
        category=InsightCategory.DATA_QUALITY,
        direction=InsightDirection.NEUTRAL,
        relationship=InsightRelationship.INSUFFICIENT_EVIDENCE,
        title_key="t",
        message_key="m",
        confidence=InsightConfidence.INSUFFICIENT_DATA,
    )
    assert insight.confidence == InsightConfidence.INSUFFICIENT_DATA


def test_dedupe_key_defaults_to_rule_id():
    insight = HistoricalInsight(
        rule_id="x",
        category=InsightCategory.SECTOR_PERFORMANCE,
        direction=InsightDirection.POSITIVE,
        relationship=InsightRelationship.OBSERVED,
        title_key="t",
        message_key="m",
        affected_sectors=("midfield",),
        confidence=InsightConfidence.INSUFFICIENT_DATA,
    )
    assert insight.dedupe_key == "x"


# --------------------------------------------------------------------------
# Sector insights
# --------------------------------------------------------------------------

def test_midfield_improvement_insight_generated():
    previous = make_snapshot(ratings=make_ratings(midfield=4.0))
    current = make_snapshot(ratings=make_ratings(midfield=6.0))
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    midfield_insight = next(
        i for i in result if i.rule_id == "sector.midfield_improvement"
    )
    assert midfield_insight.direction == InsightDirection.POSITIVE
    assert midfield_insight.confidence == InsightConfidence.HIGH
    assert midfield_insight.evidence


def test_midfield_decline_insight_generated():
    previous = make_snapshot(ratings=make_ratings(midfield=6.0))
    current = make_snapshot(ratings=make_ratings(midfield=4.0))
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    midfield_insight = next(
        i for i in result if i.rule_id == "sector.midfield_decline"
    )
    assert midfield_insight.direction == InsightDirection.NEGATIVE


def test_attack_improvement_insight_generated():
    previous = make_snapshot(
        ratings=make_ratings(left_attack=3.0, central_attack=3.0, right_attack=3.0)
    )
    current = make_snapshot(
        ratings=make_ratings(left_attack=4.0, central_attack=4.0, right_attack=4.0)
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "sector.attack_improvement" for i in result)


def test_defense_decline_insight_generated():
    previous = make_snapshot(
        ratings=make_ratings(left_defense=5.0, central_defense=5.0, right_defense=5.0)
    )
    current = make_snapshot(
        ratings=make_ratings(left_defense=3.0, central_defense=3.0, right_defense=3.0)
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "sector.defense_decline" for i in result)


def test_attack_defense_tradeoff_detected():
    previous = make_snapshot(
        ratings=make_ratings(
            left_attack=3.0, central_attack=3.0, right_attack=3.0,
            left_defense=5.0, central_defense=5.0, right_defense=5.0,
        )
    )
    current = make_snapshot(
        ratings=make_ratings(
            left_attack=4.5, central_attack=4.5, right_attack=4.5,
            left_defense=3.5, central_defense=3.5, right_defense=3.5,
        )
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    tradeoff = next(
        i for i in result if i.rule_id == "sector.attack_defense_tradeoff"
    )
    assert tradeoff.direction == InsightDirection.MIXED


def test_identical_ratings_produce_no_sector_insights():
    ratings = make_ratings()
    previous = make_snapshot(match_date="2026-07-01", ratings=ratings)
    current = make_snapshot(match_date="2026-07-08", ratings=ratings)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert not any(i.category == InsightCategory.SECTOR_PERFORMANCE for i in result)


def test_broad_improvement_detected_when_majority_of_sectors_improve():
    previous = make_snapshot(
        ratings=make_ratings(
            midfield=4.0, right_defense=4.0, central_defense=4.0, left_defense=4.0,
            right_attack=3.0, central_attack=3.0, left_attack=3.0,
        )
    )
    current = make_snapshot(
        ratings=make_ratings(
            midfield=6.0, right_defense=6.0, central_defense=6.0, left_defense=6.0,
            right_attack=3.0, central_attack=3.0, left_attack=3.0,
        )
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "sector.broad_improvement" for i in result)


# --------------------------------------------------------------------------
# Formation and lineup insights
# --------------------------------------------------------------------------

def test_parse_formation_counts():
    assert parse_formation_counts("3-5-2") == (3, 5, 2)
    assert parse_formation_counts("weird") is None
    assert parse_formation_counts("") is None


def test_formation_changed_insight():
    previous = make_snapshot(formation="4-4-2")
    current = make_snapshot(formation="3-5-2")
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "formation.changed" for i in result)


def test_formation_unchanged_no_insight():
    previous = make_snapshot(formation="3-5-2")
    current = make_snapshot(formation="3-5-2")
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert not any(i.rule_id == "formation.changed" for i in result)


def test_midfielder_count_changed_insight():
    previous = make_snapshot(formation="4-4-2")
    current = make_snapshot(formation="3-5-2")
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    slot_insight = next(
        i for i in result if i.rule_id == "formation.midfielder_count_changed"
    )
    assert slot_insight.message_params["previous"] == 4
    assert slot_insight.message_params["current"] == 5


def test_player_added_insight():
    previous = make_snapshot(lineup=[entry("Alice"), entry("Bob")])
    current = make_snapshot(lineup=[entry("Alice"), entry("Carol")])
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    added = next(i for i in result if i.rule_id == "lineup.player_added")
    assert added.message_params["player_name"] == "Carol"


def test_player_removed_insight():
    previous = make_snapshot(lineup=[entry("Alice"), entry("Bob")])
    current = make_snapshot(lineup=[entry("Alice"), entry("Carol")])
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    removed = next(i for i in result if i.rule_id == "lineup.player_removed")
    assert removed.message_params["player_name"] == "Bob"


def test_multiple_starter_changes_insight():
    previous = make_snapshot(
        lineup=[entry("A"), entry("B"), entry("C"), entry("D")]
    )
    current = make_snapshot(
        lineup=[entry("A"), entry("E"), entry("F"), entry("G")]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "lineup.multiple_starter_changes" for i in result)


def test_position_change_insight():
    previous = make_snapshot(
        lineup=[entry("Alice", position="WINGER", side="LEFT")]
    )
    current = make_snapshot(
        lineup=[entry("Alice", position="INNER_MIDFIELDER", side="CENTER")]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    position_insight = next(
        i for i in result if i.rule_id == "lineup.player_position_changed"
    )
    assert position_insight.message_params["previous_position"] == "WINGER"


def test_side_change_insight_detected_even_though_evolution_ignores_side():
    previous = make_snapshot(
        lineup=[entry("Michael", position="WINGER", side="LEFT")]
    )
    current = make_snapshot(
        lineup=[entry("Michael", position="WINGER", side="RIGHT")]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    side_insight = next(i for i in result if i.rule_id == "lineup.player_side_changed")
    assert side_insight.message_params["previous_side"] == "LEFT"
    assert side_insight.message_params["current_side"] == "RIGHT"


def test_player_reorder_produces_no_false_lineup_change():
    previous = make_snapshot(lineup=[entry("Alice", number=1), entry("Bob", number=2)])
    current = make_snapshot(lineup=[entry("Bob", number=2), entry("Alice", number=1)])
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert not any(i.category == InsightCategory.LINEUP for i in result)


def test_same_core_lineup_retained_insight():
    lineup = [entry(f"P{i}", number=i) for i in range(1, 12)]
    previous = make_snapshot(lineup=lineup)
    current = make_snapshot(lineup=lineup)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "lineup.same_core_retained" for i in result)


# --------------------------------------------------------------------------
# Individual-order insights
# --------------------------------------------------------------------------

def test_inner_midfielders_offensive_likely_contributor():
    previous = make_snapshot(
        ratings=make_ratings(midfield=4.0),
        lineup=[
            entry("Delion", position="INNER_MIDFIELDER", order="Normal"),
            entry("Abbiendi", position="INNER_MIDFIELDER", order="Normal"),
            entry("Garcia", position="INNER_MIDFIELDER", order="Normal"),
        ],
    )
    current = make_snapshot(
        ratings=make_ratings(midfield=5.5),
        lineup=[
            entry("Delion", position="INNER_MIDFIELDER", order="Offensive"),
            entry("Abbiendi", position="INNER_MIDFIELDER", order="Offensive"),
            entry("Garcia", position="INNER_MIDFIELDER", order="Offensive"),
        ],
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    contributor = next(
        i for i in result
        if i.rule_id == "order.inner_midfielders_offensive_likely_contributor"
    )
    assert contributor.relationship == InsightRelationship.LIKELY_CONTRIBUTOR
    assert contributor.message_params["count"] == 3
    assert len(contributor.evidence) == 4  # 1 sector + 3 order changes


def test_offensive_im_contributor_not_generated_without_midfield_improvement():
    previous = make_snapshot(
        ratings=make_ratings(midfield=5.0),
        lineup=[
            entry("Delion", position="INNER_MIDFIELDER", order="Normal"),
            entry("Abbiendi", position="INNER_MIDFIELDER", order="Normal"),
        ],
    )
    current = make_snapshot(
        ratings=make_ratings(midfield=5.0),
        lineup=[
            entry("Delion", position="INNER_MIDFIELDER", order="Offensive"),
            entry("Abbiendi", position="INNER_MIDFIELDER", order="Offensive"),
        ],
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert not any(
        i.rule_id == "order.inner_midfielders_offensive_likely_contributor"
        for i in result
    )


def test_forward_towards_wing_insight():
    previous = make_snapshot(
        lineup=[entry("Michael", position="FORWARD", order="Normal")]
    )
    current = make_snapshot(
        lineup=[entry("Michael", position="FORWARD", order="Towards Wing")]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "order.forward_towards_wing" for i in result)


def test_order_side_change_insight_uses_canonical_values():
    previous = make_snapshot(
        lineup=[
            entry(
                "Michael", position="FORWARD", order="Towards Wing", order_side="LEFT"
            )
        ]
    )
    current = make_snapshot(
        lineup=[
            entry(
                "Michael", position="FORWARD", order="Towards Wing", order_side="RIGHT"
            )
        ]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    order_side_insight = next(
        i for i in result if i.rule_id == "order.order_side_changed"
    )
    assert order_side_insight.evidence[0].previous_value == "LEFT"
    assert order_side_insight.evidence[0].current_value == "RIGHT"


def test_defender_order_changed_insight():
    previous = make_snapshot(
        lineup=[entry("Roberto", position="CENTRAL_DEFENDER", order="Normal")]
    )
    current = make_snapshot(
        lineup=[entry("Roberto", position="CENTRAL_DEFENDER", order="Defensive")]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "order.defender_changed" for i in result)


def test_no_false_order_change_from_reorder_alone():
    lineup = [
        entry("Alice", position="WINGER", order="Offensive", order_side="LEFT"),
    ]
    previous = make_snapshot(lineup=lineup)
    current = make_snapshot(lineup=lineup)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert not any(i.category == InsightCategory.INDIVIDUAL_ORDER for i in result)


# --------------------------------------------------------------------------
# Player condition insights
# --------------------------------------------------------------------------

def test_form_increase_insight():
    previous = make_snapshot(lineup=[entry("Alice", form=4), entry("Bob", form=5)])
    current = make_snapshot(lineup=[entry("Alice", form=6), entry("Bob", form=5)])
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "player_condition.form_increased" for i in result)


def test_stamina_decrease_insight():
    previous = make_snapshot(
        lineup=[entry("Alice", stamina=8), entry("Bob", stamina=8)]
    )
    current = make_snapshot(
        lineup=[entry("Alice", stamina=5), entry("Bob", stamina=8)]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "player_condition.stamina_decreased" for i in result)


def test_player_condition_missing_optional_data_produces_no_insight():
    previous = make_snapshot(lineup=[entry("Alice", form=None)])
    current = make_snapshot(lineup=[entry("Alice", form=None)])
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert not any(i.category == InsightCategory.PLAYER_CONDITION for i in result)


def test_form_change_aggregates_multiple_players():
    previous = make_snapshot(
        lineup=[entry("Alice", form=4), entry("Bob", form=4), entry("Carol", form=4)]
    )
    current = make_snapshot(
        lineup=[entry("Alice", form=6), entry("Bob", form=6), entry("Carol", form=4)]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    form_insight = next(
        i for i in result if i.rule_id == "player_condition.form_increased"
    )
    assert form_insight.message_params["count"] == 2


def test_skill_changed_never_uses_contributor_language():
    previous = make_snapshot(
        lineup=[entry("Alice", skills=HistoricalPlayerSkills(passing=10))]
    )
    current = make_snapshot(
        lineup=[entry("Alice", skills=HistoricalPlayerSkills(passing=12))]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    skill_insight = next(
        i for i in result if i.rule_id == "player_condition.skill_changed"
    )
    assert skill_insight.relationship == InsightRelationship.OBSERVED


# --------------------------------------------------------------------------
# Tactical insights
# --------------------------------------------------------------------------

def test_tactic_changed_insight():
    previous = make_snapshot(tactic="Normal")
    current = make_snapshot(tactic="Pressing")
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "tactic.changed" for i in result)


def test_home_away_changed_insight():
    previous = make_snapshot(home_away=HomeAway.HOME)
    current = make_snapshot(home_away=HomeAway.AWAY)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "tactic.home_away_changed" for i in result)


# --------------------------------------------------------------------------
# Prediction insights
# --------------------------------------------------------------------------

def test_win_probability_increase_insight():
    previous = make_snapshot(win_probability=0.4)
    current = make_snapshot(win_probability=0.6)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(
        i.rule_id == "prediction.win_probability_changed"
        and i.direction == InsightDirection.POSITIVE
        for i in result
    )


def test_opponent_expected_goals_increase_insight():
    previous = make_snapshot(opponent_expected_goals=1.0)
    current = make_snapshot(opponent_expected_goals=1.5)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(
        i.rule_id == "prediction.opponent_expected_goals_increased" for i in result
    )


# --------------------------------------------------------------------------
# Rule engine mechanics: no rules / one rule / priority / dedup / determinism
# --------------------------------------------------------------------------

class _AlwaysFiresRule(InsightRule):
    rule_id = "test.always_fires"
    category = InsightCategory.OVERALL
    priority = 10

    def evaluate(self, context):
        return (
            HistoricalInsight(
                rule_id=self.rule_id,
                category=self.category,
                direction=InsightDirection.NEUTRAL,
                relationship=InsightRelationship.OBSERVED,
                title_key="t",
                message_key="m",
                evidence=(),
                confidence=InsightConfidence.INSUFFICIENT_DATA,
                priority=self.priority,
            ),
        )


class _NeverFiresRule(InsightRule):
    rule_id = "test.never_fires"
    category = InsightCategory.OVERALL
    priority = 5

    def evaluate(self, context):
        return ()


def test_engine_with_no_applicable_rules_returns_empty():
    engine = InsightRuleEngine(rules=(_NeverFiresRule(),))
    previous = make_snapshot()
    current = make_snapshot()
    context = build_context(current, previous)

    assert engine.evaluate(context) == ()


def test_engine_with_one_rule():
    engine = InsightRuleEngine(rules=(_AlwaysFiresRule(),))
    previous = make_snapshot()
    current = make_snapshot()
    context = build_context(current, previous)

    result = engine.evaluate(context)
    assert len(result) == 1
    assert result[0].rule_id == "test.always_fires"


def test_engine_priority_ordering():
    class LowPriority(InsightRule):
        rule_id = "test.low"
        category = InsightCategory.OVERALL
        priority = 1

        def evaluate(self, context):
            return (
                HistoricalInsight(
                    rule_id=self.rule_id, category=self.category,
                    direction=InsightDirection.NEUTRAL,
                    relationship=InsightRelationship.OBSERVED,
                    title_key="t", message_key="m",
                    affected_sectors=("a",),
                    confidence=InsightConfidence.INSUFFICIENT_DATA,
                    priority=self.priority,
                ),
            )

    class HighPriority(InsightRule):
        rule_id = "test.high"
        category = InsightCategory.OVERALL
        priority = 99

        def evaluate(self, context):
            return (
                HistoricalInsight(
                    rule_id=self.rule_id, category=self.category,
                    direction=InsightDirection.NEUTRAL,
                    relationship=InsightRelationship.OBSERVED,
                    title_key="t", message_key="m",
                    affected_sectors=("b",),
                    confidence=InsightConfidence.INSUFFICIENT_DATA,
                    priority=self.priority,
                ),
            )

    engine = InsightRuleEngine(rules=(LowPriority(), HighPriority()))
    previous = make_snapshot()
    current = make_snapshot()
    context = build_context(current, previous)

    result = engine.evaluate(context)
    assert result[0].rule_id == "test.high"
    assert result[1].rule_id == "test.low"


def test_engine_deduplicates_same_dedupe_key_keeping_higher_priority():
    from engine.history.insights.evidence import InsightEvidence
    from engine.history.insights.enums import EvidenceType

    dummy_evidence = (
        InsightEvidence(evidence_type=EvidenceType.SECTOR_DELTA, entity_id="midfield"),
    )

    class WeakDuplicate(InsightRule):
        rule_id = "test.weak"
        category = InsightCategory.SECTOR_PERFORMANCE
        priority = 10

        def evaluate(self, context):
            return (
                HistoricalInsight(
                    rule_id=self.rule_id, category=self.category,
                    direction=InsightDirection.POSITIVE,
                    relationship=InsightRelationship.OBSERVED,
                    title_key="t", message_key="m",
                    affected_sectors=("midfield",),
                    evidence=dummy_evidence,
                    confidence=InsightConfidence.LOW,
                    priority=self.priority,
                    dedupe_key="shared.midfield_improvement",
                ),
            )

    class StrongDuplicate(InsightRule):
        rule_id = "test.strong"
        category = InsightCategory.SECTOR_PERFORMANCE
        priority = 50

        def evaluate(self, context):
            return (
                HistoricalInsight(
                    rule_id=self.rule_id, category=self.category,
                    direction=InsightDirection.POSITIVE,
                    relationship=InsightRelationship.OBSERVED,
                    title_key="t", message_key="m",
                    affected_sectors=("midfield",),
                    evidence=dummy_evidence,
                    confidence=InsightConfidence.HIGH,
                    priority=self.priority,
                    dedupe_key="shared.midfield_improvement",
                ),
            )

    engine = InsightRuleEngine(rules=(WeakDuplicate(), StrongDuplicate()))
    previous = make_snapshot()
    current = make_snapshot()
    context = build_context(current, previous)

    result = engine.evaluate(context)
    assert len(result) == 1
    assert result[0].rule_id == "test.strong"


def test_engine_mutually_exclusive_insights_resolved_by_priority():
    class LowerId(InsightRule):
        rule_id = "test.mutex_low"
        category = InsightCategory.OVERALL
        priority = 10

        def evaluate(self, context):
            return (
                HistoricalInsight(
                    rule_id=self.rule_id, category=self.category,
                    direction=InsightDirection.NEUTRAL,
                    relationship=InsightRelationship.OBSERVED,
                    title_key="t", message_key="m",
                    affected_sectors=("x",),
                    confidence=InsightConfidence.INSUFFICIENT_DATA,
                    priority=self.priority,
                    excludes=("test.mutex_high",),
                ),
            )

    class HigherId(InsightRule):
        rule_id = "test.mutex_high"
        category = InsightCategory.OVERALL
        priority = 20

        def evaluate(self, context):
            return (
                HistoricalInsight(
                    rule_id=self.rule_id, category=self.category,
                    direction=InsightDirection.NEUTRAL,
                    relationship=InsightRelationship.OBSERVED,
                    title_key="t", message_key="m",
                    affected_sectors=("y",),
                    confidence=InsightConfidence.INSUFFICIENT_DATA,
                    priority=self.priority,
                ),
            )

    engine = InsightRuleEngine(rules=(LowerId(), HigherId()))
    previous = make_snapshot()
    current = make_snapshot()
    context = build_context(current, previous)

    result = engine.evaluate(context)
    rule_ids = {insight.rule_id for insight in result}
    assert rule_ids == {"test.mutex_high"}


def test_engine_output_is_deterministic_across_runs():
    engine = InsightRuleEngine()
    previous = make_snapshot(
        ratings=make_ratings(midfield=4.0), formation="4-4-2",
        lineup=[entry("Alice", form=4), entry("Bob")],
    )
    current = make_snapshot(
        ratings=make_ratings(midfield=6.0), formation="3-5-2",
        lineup=[entry("Alice", form=7), entry("Carol")],
    )
    context = build_context(current, previous)

    first_run = [i.rule_id for i in engine.evaluate(context)]
    second_run = [i.rule_id for i in engine.evaluate(context)]

    assert first_run == second_run


# --------------------------------------------------------------------------
# generate_insights() end-to-end + validation
# --------------------------------------------------------------------------

def test_generate_insights_end_to_end():
    previous = make_snapshot(ratings=make_ratings(midfield=4.0))
    current = make_snapshot(ratings=make_ratings(midfield=6.0))
    evolution = compare(current, previous)

    result = generate_insights(
        current, previous, evolution, comparison_target_key="previous_league_match"
    )

    assert result.current_snapshot_id == current.snapshot_id
    assert result.previous_snapshot_id == previous.snapshot_id
    assert any(i.rule_id == "sector.midfield_improvement" for i in result.insights)
    assert result.summary.comparison_target_key == "previous_league_match"


def test_generate_insights_rejects_mismatched_evolution():
    previous = make_snapshot()
    current = make_snapshot()
    other_previous = make_snapshot()
    evolution = compare(current, other_previous)

    with pytest.raises(InsightGenerationError):
        generate_insights(current, previous, evolution)


def test_generate_insights_serializes_to_dict():
    import json

    previous = make_snapshot(ratings=make_ratings(midfield=4.0))
    current = make_snapshot(ratings=make_ratings(midfield=6.0))
    evolution = compare(current, previous)
    result = generate_insights(current, previous, evolution)

    payload = json.dumps(result.to_dict())
    assert "insights" in payload
    assert "summary" in payload


# --------------------------------------------------------------------------
# Executive summary
# --------------------------------------------------------------------------

def test_summary_improvement():
    previous = make_snapshot(ratings=make_ratings(midfield=4.0))
    current = make_snapshot(ratings=make_ratings(midfield=6.0))
    evolution = compare(current, previous)
    insights = InsightRuleEngine().evaluate(
        InsightContext(current, previous, evolution)
    )

    summary = build_executive_summary(evolution, insights, "previous_league_match")

    assert summary.overall_direction == InsightDirection.POSITIVE
    assert summary.main_improvement is not None
    assert summary.main_improvement.rule_id == "sector.midfield_improvement"


def test_summary_decline():
    previous = make_snapshot(ratings=make_ratings(midfield=6.0))
    current = make_snapshot(ratings=make_ratings(midfield=4.0))
    evolution = compare(current, previous)
    insights = InsightRuleEngine().evaluate(
        InsightContext(current, previous, evolution)
    )

    summary = build_executive_summary(evolution, insights, "previous_match")

    assert summary.overall_direction == InsightDirection.NEGATIVE
    assert summary.main_decline is not None


def test_summary_mixed_result():
    previous = make_snapshot(
        ratings=make_ratings(midfield=4.0, central_attack=6.0)
    )
    current = make_snapshot(
        ratings=make_ratings(midfield=6.0, central_attack=4.0)
    )
    evolution = compare(current, previous)
    insights = InsightRuleEngine().evaluate(
        InsightContext(current, previous, evolution)
    )

    summary = build_executive_summary(evolution, insights, "previous_match")

    assert summary.overall_direction == InsightDirection.MIXED
    assert summary.main_improvement is not None
    assert summary.main_decline is not None


def test_summary_no_significant_change():
    ratings = make_ratings()
    previous = make_snapshot(match_date="2026-07-01", ratings=ratings)
    current = make_snapshot(match_date="2026-07-08", ratings=ratings)
    evolution = compare(current, previous)
    insights = InsightRuleEngine().evaluate(
        InsightContext(current, previous, evolution)
    )

    summary = build_executive_summary(evolution, insights, "previous_match")

    assert summary.overall_direction == InsightDirection.NEUTRAL
    assert summary.main_improvement is None
    assert summary.main_decline is None


def test_summary_missing_ratings_reports_limitation():
    previous = make_snapshot(ratings=SectorRatings())
    current = make_snapshot(ratings=make_ratings(midfield=6.0))
    evolution = compare(current, previous)
    insights = InsightRuleEngine().evaluate(
        InsightContext(current, previous, evolution)
    )

    summary = build_executive_summary(evolution, insights, "previous_match")

    assert summary.limitation_key == "insight.limitation.missing_ratings"


def test_ensure_insight_context_valid_rejects_missing_current():
    from engine.history.insights.validation import ensure_insight_context_valid

    previous = make_snapshot()
    current = make_snapshot()
    evolution = compare(current, previous)
    context = InsightContext(current_snapshot=None, previous_snapshot=previous, evolution=evolution)
    with pytest.raises(InsightGenerationError):
        ensure_insight_context_valid(context)


def test_ensure_insight_context_valid_rejects_missing_previous():
    from engine.history.insights.validation import ensure_insight_context_valid

    previous = make_snapshot()
    current = make_snapshot()
    evolution = compare(current, previous)
    context = InsightContext(current_snapshot=current, previous_snapshot=None, evolution=evolution)
    with pytest.raises(InsightGenerationError):
        ensure_insight_context_valid(context)


def test_ensure_insight_context_valid_rejects_missing_evolution():
    from engine.history.insights.validation import ensure_insight_context_valid

    previous = make_snapshot()
    current = make_snapshot()
    context = InsightContext(current_snapshot=current, previous_snapshot=previous, evolution=None)
    with pytest.raises(InsightGenerationError):
        ensure_insight_context_valid(context)


def test_base_insight_rule_not_implemented():
    previous = make_snapshot()
    current = make_snapshot()
    context = build_context(current, previous)
    with pytest.raises(NotImplementedError):
        InsightRule().evaluate(context)


def test_defender_and_forward_count_changed_insights():
    previous = make_snapshot(formation="5-4-1")
    current = make_snapshot(formation="3-5-2")
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "formation.defender_count_changed" for i in result)
    assert any(i.rule_id == "formation.forward_count_changed" for i in result)


def test_same_formation_different_ratings_insight():
    previous = make_snapshot(formation="3-5-2", ratings=make_ratings(midfield=4.0))
    current = make_snapshot(formation="3-5-2", ratings=make_ratings(midfield=8.0))
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(
        i.rule_id == "formation.same_formation_different_ratings" for i in result
    )


def test_winger_order_changed_insight():
    previous = make_snapshot(
        lineup=[entry("Nahuel", position="WINGER", order="Normal")]
    )
    current = make_snapshot(
        lineup=[entry("Nahuel", position="WINGER", order="Offensive")]
    )
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "order.winger_changed" for i in result)


def test_experience_changed_insight():
    previous = make_snapshot(lineup=[entry("Alice", experience=3)])
    current = make_snapshot(lineup=[entry("Alice", experience=5)])
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "player_condition.experience_changed" for i in result)


def test_expected_goals_and_possession_prediction_insights():
    previous = make_snapshot(expected_goals=1.0, possession=45.0)
    current = make_snapshot(expected_goals=1.8, possession=55.0)
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "prediction.expected_goals_changed" for i in result)
    assert any(i.rule_id == "prediction.possession_changed" for i in result)


def test_tactic_level_and_attitude_and_confidence_changed_insights():
    previous = make_snapshot(tactic_level=3.0, attitude="Normal", confidence="Low")
    current = make_snapshot(tactic_level=6.0, attitude="Attacking", confidence="High")
    context = build_context(current, previous)

    result = InsightRuleEngine().evaluate(context)

    assert any(i.rule_id == "tactic.level_changed" for i in result)
    assert any(i.rule_id == "tactic.attitude_changed" for i in result)
    assert any(i.rule_id == "tactic.confidence_changed" for i in result)
    previous = make_snapshot(
        ratings=make_ratings(midfield=4.0),
        lineup=[
            entry("Delion", position="INNER_MIDFIELDER", order="Normal"),
            entry("Abbiendi", position="INNER_MIDFIELDER", order="Normal"),
        ],
    )
    current = make_snapshot(
        ratings=make_ratings(midfield=5.5),
        lineup=[
            entry("Delion", position="INNER_MIDFIELDER", order="Offensive"),
            entry("Abbiendi", position="INNER_MIDFIELDER", order="Offensive"),
        ],
    )
    evolution = compare(current, previous)
    insights = InsightRuleEngine().evaluate(
        InsightContext(current, previous, evolution)
    )

    summary = build_executive_summary(evolution, insights, "previous_match")

    assert summary.strongest_contributor is not None
    assert summary.strongest_contributor.relationship in (
        InsightRelationship.LIKELY_CONTRIBUTOR,
        InsightRelationship.POSSIBLE_CONTRIBUTOR,
    )
