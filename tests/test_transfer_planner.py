import os
import tempfile
import unittest
from pathlib import Path

from engine.squad_evolution.models import (
    AGE_BAND_LATE_CAREER,
    AGE_BAND_PRIME,
    AGE_BAND_VETERAN,
    HORIZON_MEDIUM_TERM,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MODERATE,
    SUCCESSION_DEVELOPMENT,
    SUCCESSION_EMERGENCY,
    SUCCESSION_NEAR_READY,
    SUCCESSION_NONE,
    SUCCESSION_READY_NOW,
    TRAINING_DEFENDING,
    TRAINING_PLAYMAKING,
    DependencyResult,
    IdentityContinuityResult,
    SquadEvolutionResult,
    SuccessionMapRow,
    TrainingAlignmentResult,
)
from engine.transfer_planner.catalogs import ROLE_PROFILE_TEMPLATES
from engine.transfer_planner.models import (
    ACTION_BUY_NOW,
    ACTION_DEVELOP_INTERNALLY,
    ACTION_MONITOR,
    AGE_STRATEGY_IMMEDIATE,
    AGE_STRATEGY_YOUTH,
    BUDGET_FLEXIBLE,
    BUDGET_UNSPECIFIED,
    NEED_DEVELOPMENT_PROSPECT,
    NEED_IMMEDIATE_STARTER,
    NEED_NONE,
    NEED_SPECIALIST,
    NEED_STARTER_COMPETITION,
    OBJECTIVE_BALANCED,
    OBJECTIVE_PROMOTION_PUSH,
    SPECIALTY_NO_PREFERENCE,
    TRAINING_PREF_ANY,
    TransferConstraints,
)
from engine.transfer_planner.planner import TransferPlanner
from ht_coach_app.persistence.match_workspace_repository import (
    MatchWorkspaceRepository,
    MatchWorkspaceSettings,
)
from ht_coach_app.services.transfer_planner_service import TransferPlannerService


def succession_row(
    role,
    *,
    structural_risk=RISK_LOW,
    operational_risk=RISK_LOW,
    readiness=SUCCESSION_NONE,
    depth=2,
    age_band=AGE_BAND_PRIME,
    temporary_issue=False,
    structural_gap=False,
):
    return SuccessionMapRow(
        role=role,
        full_strength_starter=f"{role} Starter",
        current_available_starter=f"{role} Available",
        primary_backup=f"{role} Backup" if depth > 1 else "",
        potential_successor=f"{role} Prospect"
        if readiness in {SUCCESSION_READY_NOW, SUCCESSION_NEAR_READY, SUCCESSION_DEVELOPMENT}
        else "",
        starter_age_band=age_band,
        current_depth=depth,
        succession_readiness=readiness,
        operational_risk=operational_risk,
        structural_risk=structural_risk,
        temporary_issue=temporary_issue,
        structural_gap=structural_gap,
        explanation=f"{role} test risk",
    )


def evolution_result(rows, *, training=TRAINING_PLAYMAKING, identity="Midfield Dominant Squad"):
    return SquadEvolutionResult(
        planning_horizon=HORIZON_MEDIUM_TERM,
        succession_map=tuple(rows),
        dependencies=(
            DependencyResult(
                key_player="Central Defense Starter",
                role="Central Defense",
                dependency_level=RISK_CRITICAL,
                current_impact="High",
                structural_impact="High",
                successor_status="No successor",
                reason="Single point of failure",
            ),
        ),
        training_alignment=TrainingAlignmentResult(
            current_training=training,
            strongly_supports=("Midfield",),
            not_addressed=("Central Defense", "Goalkeeper"),
        ),
        identity_continuity=IdentityContinuityResult(
            current_identity=identity,
            continuity="watch",
            reason="Test identity",
            key_contributors=("Midfield Starter",),
        ),
    )


class TransferPlannerTest(unittest.TestCase):
    def test_critical_structural_gap_generates_immediate_profile_not_exact_delta(self):
        result = TransferPlanner().build_plan(
            evolution_result(
                [
                    succession_row(
                        "Central Defense",
                        structural_risk=RISK_CRITICAL,
                        operational_risk=RISK_HIGH,
                        readiness=SUCCESSION_NONE,
                        depth=1,
                        structural_gap=True,
                    ),
                    succession_row("Midfield"),
                ]
            )
        )

        top = result.needs[0]
        self.assertEqual(top.role, "Central Defense")
        self.assertEqual(top.need_type, NEED_IMMEDIATE_STARTER)
        self.assertEqual(top.recommended_action, ACTION_BUY_NOW)
        self.assertEqual(top.recommended_profile.position, "Central Defender")
        self.assertIn("defending", top.recommended_profile.primary_skill.skill)
        self.assertIn("No exact performance delta", top.impact_projection.no_exact_delta_statement)
        self.assertIn("live market data", result.summary.summary_sentences[-1])

    def test_ready_internal_solution_prefers_internal_development(self):
        result = TransferPlanner().build_plan(
            evolution_result(
                [
                    succession_row(
                        "Midfield",
                        structural_risk=RISK_HIGH,
                        readiness=SUCCESSION_NEAR_READY,
                        depth=2,
                    )
                ]
            )
        )

        self.assertEqual(result.needs[0].recommended_action, ACTION_DEVELOP_INTERNALLY)

    def test_temporary_operational_issue_is_monitored(self):
        result = TransferPlanner().build_plan(
            evolution_result(
                [
                    succession_row(
                        "Winger",
                        structural_risk=RISK_LOW,
                        operational_risk=RISK_HIGH,
                        readiness=SUCCESSION_READY_NOW,
                        temporary_issue=True,
                    )
                ]
            )
        )

        self.assertIn(
            result.needs[0].recommended_action,
            {ACTION_MONITOR, ACTION_DEVELOP_INTERNALLY},
        )

    def test_development_readiness_generates_development_profile(self):
        result = TransferPlanner().build_plan(
            evolution_result(
                [
                    succession_row(
                        "Forward",
                        structural_risk=RISK_LOW,
                        operational_risk=RISK_LOW,
                        readiness=SUCCESSION_DEVELOPMENT,
                        depth=3,
                    )
                ]
            ),
            TransferConstraints(preferred_age_strategy=AGE_STRATEGY_YOUTH),
        )

        self.assertEqual(result.needs[0].need_type, NEED_DEVELOPMENT_PROSPECT)
        self.assertEqual(result.needs[0].recommended_profile.age_range, "17-20")

    def test_objective_changes_profile_type_for_promotion_push(self):
        rows = [
            succession_row(
                "Goalkeeper",
                structural_risk=RISK_MODERATE,
                operational_risk=RISK_LOW,
                depth=3,
            ),
            succession_row(
                "Forward",
                structural_risk=RISK_LOW,
                operational_risk=RISK_MODERATE,
                depth=1,
            ),
        ]

        balanced = TransferPlanner().build_plan(
            evolution_result(rows),
            TransferConstraints(planning_objective=OBJECTIVE_BALANCED),
        )
        promotion = TransferPlanner().build_plan(
            evolution_result(rows),
            TransferConstraints(planning_objective=OBJECTIVE_PROMOTION_PUSH),
        )

        balanced_forward = next(need for need in balanced.needs if need.role == "Forward")
        promotion_forward = next(need for need in promotion.needs if need.role == "Forward")

        self.assertEqual(balanced_forward.need_type, NEED_SPECIALIST)
        self.assertEqual(promotion_forward.need_type, NEED_STARTER_COMPETITION)

    def test_profile_generation_covers_every_supported_role(self):
        rows = [
            succession_row(
                role,
                structural_risk=RISK_HIGH,
                readiness=SUCCESSION_EMERGENCY,
                depth=1,
            )
            for role in ROLE_PROFILE_TEMPLATES
        ]

        result = TransferPlanner().build_plan(evolution_result(rows, training=TRAINING_DEFENDING))

        self.assertEqual(
            {need.role for need in result.needs},
            set(ROLE_PROFILE_TEMPLATES),
        )
        self.assertTrue(all(need.recommended_profile for need in result.needs))
        self.assertEqual(
            {need.recommended_profile.position for need in result.needs},
            {template["position"] for template in ROLE_PROFILE_TEMPLATES.values()},
        )

    def test_constraints_normalization_and_service_cache(self):
        service = TransferPlannerService()
        constraints = service.normalize_constraints(
            TransferConstraints(
                planning_objective="bad",
                budget_tier="bad",
                preferred_age_strategy=AGE_STRATEGY_IMMEDIATE,
                training_compatibility_preference="bad",
                specialty_preference="bad",
            )
        )

        self.assertEqual(constraints.planning_objective, OBJECTIVE_BALANCED)
        self.assertEqual(constraints.budget_tier, BUDGET_UNSPECIFIED)
        self.assertEqual(constraints.training_compatibility_preference, TRAINING_PREF_ANY)
        self.assertEqual(constraints.specialty_preference, SPECIALTY_NO_PREFERENCE)

        evolution = evolution_result([succession_row("Central Defense", structural_risk=RISK_HIGH)])
        first = service.build_plan(evolution, constraints)
        second = service.build_plan(evolution, constraints)
        self.assertIs(first, second)

    def test_workspace_settings_persist_transfer_preferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = MatchWorkspaceRepository(Path(temp_dir) / "settings.json")
            repository.save(
                MatchWorkspaceSettings(
                    transfer_planning_objective=OBJECTIVE_PROMOTION_PUSH,
                    transfer_budget_tier=BUDGET_FLEXIBLE,
                    transfer_age_strategy=AGE_STRATEGY_YOUTH,
                    transfer_training_preference="prefer_compatible",
                    transfer_specialty_preference="Quick",
                )
            )

            settings = repository.load()

        self.assertEqual(settings.transfer_planning_objective, OBJECTIVE_PROMOTION_PUSH)
        self.assertEqual(settings.transfer_budget_tier, BUDGET_FLEXIBLE)
        self.assertEqual(settings.transfer_age_strategy, AGE_STRATEGY_YOUTH)
        self.assertEqual(settings.transfer_training_preference, "prefer_compatible")
        self.assertEqual(settings.transfer_specialty_preference, "Quick")

    def test_no_need_result_does_not_require_external_profile(self):
        result = TransferPlanner().build_plan(
            evolution_result(
                [
                    succession_row(
                        "Goalkeeper",
                        structural_risk=RISK_LOW,
                        operational_risk=RISK_LOW,
                        readiness=SUCCESSION_READY_NOW,
                        depth=3,
                        age_band=AGE_BAND_VETERAN,
                    )
                ]
            )
        )

        self.assertEqual(result.needs[0].need_type, NEED_NONE)
        self.assertIsNone(result.needs[0].recommended_profile)


@unittest.skipUnless(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    "PySide6 view smoke test runs only in offscreen mode",
)
class TransferPlannerViewSmokeTest(unittest.TestCase):
    def test_squad_page_contains_transfer_planner_tab(self):
        from PySide6.QtWidgets import QApplication

        from ht_coach_app.views.squad_page import SquadPage

        app = QApplication.instance() or QApplication([])
        page = SquadPage()
        labels = [page.tabs.tabText(index) for index in range(page.tabs.count())]

        self.assertIn("Transfer Planner", labels)
        self.assertTrue(page.transfer_objective_combo is not None)
