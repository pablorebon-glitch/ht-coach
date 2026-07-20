from engine.squad_evolution.models import (
    HORIZON_CURRENT,
    HORIZON_MEDIUM_TERM,
    HORIZON_SHORT_TERM,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MODERATE,
    SUCCESSION_DEVELOPMENT,
    SUCCESSION_EMERGENCY,
    SUCCESSION_NEAR_READY,
    SUCCESSION_NONE,
    SUCCESSION_READY_NOW,
    TRAINING_UNKNOWN,
)
from engine.transfer_planner.catalogs import (
    ROLE_PROFILE_TEMPLATES,
    ROLE_TO_TRAINING,
    normalize_constraints,
)
from engine.transfer_planner.models import (
    ACTION_BUY_NOW,
    ACTION_DEVELOP_INTERNALLY,
    ACTION_MONITOR,
    ACTION_NONE,
    ACTION_RECRUIT_DEVELOP,
    AGE_STRATEGY_IMMEDIATE,
    AGE_STRATEGY_TRAINABLE,
    AGE_STRATEGY_YOUTH,
    BUDGET_RESTRICTED,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    IMPACT_LIMITED,
    IMPACT_MAJOR,
    IMPACT_MEANINGFUL,
    IMPACT_MODERATE,
    INTERNAL_DEVELOPMENT,
    INTERNAL_EMERGENCY,
    INTERNAL_NEAR_READY,
    INTERNAL_NONE,
    INTERNAL_READY,
    NEED_DEVELOPMENT_PROSPECT,
    NEED_IMMEDIATE_STARTER,
    NEED_NONE,
    NEED_RELIABLE_BACKUP,
    NEED_ROTATION_DEPTH,
    NEED_SPECIALIST,
    NEED_STARTER_COMPETITION,
    NEED_SUCCESSION_REPLACEMENT,
    OBJECTIVE_IMMEDIATE_STABILITY,
    OBJECTIVE_LONG_TERM_DEVELOPMENT,
    OBJECTIVE_PROMOTION_PUSH,
    OBJECTIVE_SQUAD_RENEWAL,
    ProfileImpactProjection,
    NoActionScenario,
    PlayerProfile,
    SkillRequirement,
    TransferNeed,
    TransferPlanResult,
    TransferPlanSummary,
    URGENCY_CRITICAL,
    URGENCY_HIGH,
    URGENCY_LOW,
    URGENCY_MEDIUM,
    URGENCY_MONITOR,
)


RISK_TO_URGENCY = {
    RISK_CRITICAL: URGENCY_CRITICAL,
    RISK_HIGH: URGENCY_HIGH,
    RISK_MODERATE: URGENCY_MEDIUM,
    RISK_LOW: URGENCY_MONITOR,
}

URGENCY_WEIGHT = {
    URGENCY_CRITICAL: 5,
    URGENCY_HIGH: 4,
    URGENCY_MEDIUM: 3,
    URGENCY_LOW: 2,
    URGENCY_MONITOR: 1,
}


class TransferPlanner:
    def build_plan(self, evolution_result, constraints=None):
        constraints = normalize_constraints(constraints)
        if evolution_result is None:
            return TransferPlanResult(constraints=constraints)

        dependencies = {
            dependency.role: dependency
            for dependency in evolution_result.dependencies
        }
        identity_roles = self._identity_roles(
            evolution_result.identity_continuity.current_identity
        )
        needs = [
            self._need_from_succession(
                row,
                dependencies.get(row.role),
                evolution_result,
                constraints,
                identity_roles,
            )
            for row in evolution_result.succession_map
            if row.role in ROLE_PROFILE_TEMPLATES
        ]
        ranked = self._rank(needs, constraints)
        ranked = [
            self._with_rank(need, index + 1)
            for index, need in enumerate(ranked)
        ]
        return TransferPlanResult(
            constraints=constraints,
            summary=self._summary(ranked, evolution_result, constraints),
            needs=tuple(ranked),
        )

    def _need_from_succession(
        self,
        row,
        dependency,
        evolution,
        constraints,
        identity_roles,
    ):
        internal = self._internal_solution(row.succession_readiness)
        structural_or_temporary = self._need_nature(row)
        urgency = self._urgency(row, constraints)
        need_type = self._need_type(row, internal, constraints)
        target_role = self._target_role(need_type)
        action = self._action(urgency, structural_or_temporary, internal, need_type)
        training_support = (
            "addressed"
            if row.role in evolution.training_alignment.strongly_supports
            else "not_addressed"
        )
        identity_relevance = (
            "core_identity_support"
            if row.role in identity_roles
            else "identity_neutral"
        )
        formation_relevance = self._formation_relevance(
            evolution,
            row.role,
        )
        profile = None
        if need_type != NEED_NONE:
            profile = self._profile(
                row,
                target_role,
                constraints,
                evolution.training_alignment.current_training,
                identity_relevance,
                formation_relevance,
            )
        impact = self._impact(row, dependency, training_support)
        confidence, confidence_reasons, limitations = self._confidence(
            row,
            evolution,
        )
        alternatives = ()
        if need_type != NEED_NONE:
            alternatives = self._alternatives(
                row,
                target_role,
                constraints,
                evolution.training_alignment.current_training,
                identity_relevance,
                formation_relevance,
            )

        return TransferNeed(
            need_id=self._need_id(row.role),
            role=row.role,
            position_family=ROLE_PROFILE_TEMPLATES[row.role]["position"],
            priority_rank=0,
            urgency=urgency,
            planning_horizon=row.planning_horizon
            if hasattr(row, "planning_horizon")
            else evolution.planning_horizon,
            need_type=need_type,
            target_squad_role=target_role,
            reason_keys=(row.explanation,),
            source_risks=tuple(
                risk
                for risk in (row.operational_risk, row.structural_risk)
                if risk != RISK_LOW
            ),
            structural_or_temporary=structural_or_temporary,
            internal_solution_status=internal,
            training_support=training_support,
            identity_relevance=identity_relevance,
            formation_relevance=formation_relevance,
            recommended_action=action,
            recommended_profile=profile,
            alternative_profiles=alternatives,
            impact_projection=impact,
            confidence=confidence,
            confidence_reasons=confidence_reasons,
            data_limitations=limitations,
            no_action_scenario=self._no_action(row, need_type),
        )

    def _need_nature(self, row):
        if row.structural_risk in {RISK_HIGH, RISK_CRITICAL} or row.structural_gap:
            return "structural"
        if row.temporary_issue and row.operational_risk != RISK_LOW:
            return "temporary"
        return "no_need"

    def _need_type(self, row, internal, constraints):
        if row.structural_risk == RISK_CRITICAL and internal in {
            INTERNAL_NONE,
            INTERNAL_EMERGENCY,
        }:
            return NEED_IMMEDIATE_STARTER
        if row.starter_age_band in {"veteran", "late_career"} and internal in {
            INTERNAL_NONE,
            INTERNAL_EMERGENCY,
        }:
            return NEED_SUCCESSION_REPLACEMENT
        if row.structural_risk in {RISK_HIGH, RISK_CRITICAL}:
            return NEED_RELIABLE_BACKUP
        if internal == INTERNAL_DEVELOPMENT:
            return NEED_DEVELOPMENT_PROSPECT
        if row.operational_risk in {RISK_HIGH, RISK_CRITICAL}:
            return NEED_ROTATION_DEPTH
        if constraints.planning_objective == OBJECTIVE_PROMOTION_PUSH and row.current_depth <= 2:
            return NEED_STARTER_COMPETITION
        if row.structural_risk == RISK_MODERATE:
            return NEED_RELIABLE_BACKUP
        if row.role in {"Winger", "Forward"} and row.current_depth <= 1:
            return NEED_SPECIALIST
        return NEED_NONE

    def _urgency(self, row, constraints):
        risk = max(
            (row.structural_risk, row.operational_risk),
            key=lambda item: {
                RISK_LOW: 0,
                RISK_MODERATE: 1,
                RISK_HIGH: 2,
                RISK_CRITICAL: 3,
            }[item],
        )
        urgency = RISK_TO_URGENCY[risk]
        if (
            constraints.planning_objective == OBJECTIVE_IMMEDIATE_STABILITY
            and row.operational_risk == RISK_HIGH
        ):
            return URGENCY_HIGH
        return urgency

    def _internal_solution(self, readiness):
        return {
            SUCCESSION_READY_NOW: INTERNAL_READY,
            SUCCESSION_NEAR_READY: INTERNAL_NEAR_READY,
            SUCCESSION_DEVELOPMENT: INTERNAL_DEVELOPMENT,
            SUCCESSION_EMERGENCY: INTERNAL_EMERGENCY,
            SUCCESSION_NONE: INTERNAL_NONE,
        }.get(readiness, "unknown")

    def _target_role(self, need_type):
        return {
            NEED_IMMEDIATE_STARTER: "Immediate Starter",
            NEED_STARTER_COMPETITION: "Starter Candidate",
            NEED_ROTATION_DEPTH: "Rotation Player",
            NEED_RELIABLE_BACKUP: "Reliable Backup",
            NEED_SUCCESSION_REPLACEMENT: "Immediate Starter",
            NEED_DEVELOPMENT_PROSPECT: "Development Prospect",
            NEED_SPECIALIST: "Specialist",
            NEED_NONE: "No Transfer Needed",
        }[need_type]

    def _action(self, urgency, nature, internal, need_type):
        if need_type == NEED_NONE:
            return ACTION_NONE
        if internal in {INTERNAL_READY, INTERNAL_NEAR_READY} and urgency != URGENCY_CRITICAL:
            return ACTION_DEVELOP_INTERNALLY
        if internal == INTERNAL_DEVELOPMENT and need_type == NEED_DEVELOPMENT_PROSPECT:
            return ACTION_DEVELOP_INTERNALLY
        if nature == "temporary":
            return ACTION_MONITOR
        if urgency in {URGENCY_CRITICAL, URGENCY_HIGH} and internal in {
            INTERNAL_NONE,
            INTERNAL_EMERGENCY,
        }:
            return ACTION_BUY_NOW
        if need_type == NEED_DEVELOPMENT_PROSPECT:
            return ACTION_RECRUIT_DEVELOP
        return ACTION_MONITOR

    def _profile(
        self,
        row,
        target_role,
        constraints,
        training_focus,
        identity_relevance,
        formations,
    ):
        template = ROLE_PROFILE_TEMPLATES[row.role]
        levels = self._skill_levels(target_role, constraints)
        training_compatibility = self._training_compatibility(
            row.role,
            training_focus,
        )
        return PlayerProfile(
            position=template["position"],
            target_role=target_role,
            age_range=self._age_range(target_role, constraints),
            primary_skill=SkillRequirement(
                skill=template["primary"],
                minimum_level=levels[0],
                preferred_level=levels[1],
                stretch_level=levels[2],
            ),
            secondary_skills=tuple(
                SkillRequirement(
                    skill=skill,
                    minimum_level="Inadequate",
                    preferred_level="Passable",
                    stretch_level="Solid",
                )
                for skill in template["secondary"]
            ),
            optional_skills=tuple(template["optional"]),
            specialty_preferences=self._specialties(row.role, constraints),
            experience_preference=(
                "Useful" if target_role in {"Immediate Starter", "Reliable Backup"} else ""
            ),
            leadership_preference="Optional",
            training_compatibility=training_compatibility,
            formation_compatibility=formations,
            identity_compatibility=identity_relevance,
            profile_rationale=(
                "Profile addresses structural squad planning needs without projecting exact performance gains."
            ),
            tradeoffs=self._tradeoffs(row, training_compatibility),
            confidence=CONFIDENCE_MEDIUM,
        )

    def _alternatives(
        self,
        row,
        target_role,
        constraints,
        training_focus,
        identity_relevance,
        formations,
    ):
        if target_role == "Development Prospect":
            return ()
        restricted = self._profile(
            row,
            "Reliable Backup",
            constraints,
            training_focus,
            identity_relevance,
            formations,
        )
        developmental = self._profile(
            row,
            "Development Prospect",
            constraints,
            training_focus,
            identity_relevance,
            formations,
        )
        if constraints.budget_tier == BUDGET_RESTRICTED:
            return (restricted,)
        return (restricted, developmental)

    def _skill_levels(self, target_role, constraints):
        if target_role == "Immediate Starter":
            return ("Solid", "Excellent", "Formidable")
        if target_role == "Starter Candidate":
            return ("Solid", "Solid", "Excellent")
        if target_role == "Reliable Backup":
            return ("Passable", "Solid", "Excellent")
        if target_role == "Development Prospect":
            return ("Inadequate", "Passable", "Solid")
        return ("Passable", "Solid", "Excellent")

    def _age_range(self, target_role, constraints):
        strategy = constraints.preferred_age_strategy
        if strategy == AGE_STRATEGY_YOUTH:
            return "17-20"
        if strategy == AGE_STRATEGY_TRAINABLE:
            return "17-22"
        if target_role == "Development Prospect":
            return "17-22"
        if strategy == AGE_STRATEGY_IMMEDIATE:
            return "23-31"
        if target_role == "Immediate Starter":
            return "21-29"
        if target_role == "Reliable Backup":
            return "22-32"
        return "19-27"

    def _training_compatibility(self, role, training_focus):
        if training_focus == TRAINING_UNKNOWN:
            return "unknown"
        if training_focus in ROLE_TO_TRAINING.get(role, ()):
            return "strongly_compatible"
        if role in {"Midfield", "Winger", "Forward"} and training_focus == "passing":
            return "compatible"
        return "neutral"

    def _specialties(self, role, constraints):
        if constraints.specialty_preference != "no_preference":
            return (constraints.specialty_preference,)
        if role == "Central Defense":
            return ("Header preferred",)
        if role == "Winger":
            return ("Quick optional",)
        if role == "Forward":
            return ("Technical optional", "Unpredictable optional")
        return ()

    def _tradeoffs(self, row, training_compatibility):
        tradeoffs = []
        if row.current_depth <= 1:
            tradeoffs.append("Prioritizes immediate depth over optional versatility.")
        if row.structural_gap:
            tradeoffs.append("Addresses structural risk before luxury upgrades.")
        if row.temporary_issue:
            tradeoffs.append("May be less urgent once temporary availability improves.")
        if training_compatibility in {"neutral", "poorly_compatible", "unknown"}:
            tradeoffs.append("May not align strongly with the current training focus.")
        return tuple(tradeoffs)

    def _impact(self, row, dependency, training_support):
        dimensions = []
        if row.structural_risk != RISK_LOW:
            dimensions.append("Succession Risk")
        if dependency is not None:
            dimensions.append("Dependency Risk")
        if row.operational_risk != RISK_LOW:
            dimensions.append("Current Coverage")
        dimensions.append("Formation Flexibility")
        if training_support == "not_addressed":
            dimensions.append("Training Pipeline")
        if row.starter_age_band in {"veteran", "late_career"}:
            dimensions.append("Age Balance")
        qualitative = (
            IMPACT_MAJOR
            if row.structural_risk == RISK_CRITICAL
            else IMPACT_MEANINGFUL
            if row.structural_risk == RISK_HIGH
            else IMPACT_MODERATE
            if row.operational_risk != RISK_LOW
            else IMPACT_LIMITED
        )
        return ProfileImpactProjection(
            qualitative_impact=qualitative,
            dimensions=tuple(dict.fromkeys(dimensions)),
        )

    def _confidence(self, row, evolution):
        limitations = []
        reasons = []
        if row.starter_age_band == "unknown":
            limitations.append("Starter age is unknown.")
        if evolution.training_alignment.current_training == TRAINING_UNKNOWN:
            limitations.append("Training focus is unknown.")
        if not row.full_strength_starter:
            limitations.append("Full-strength starter hierarchy is incomplete.")
        if limitations:
            return CONFIDENCE_LOW, tuple(reasons), tuple(limitations)
        if row.full_strength_starter and row.current_depth >= 2:
            reasons.append("Starter hierarchy and depth data are available.")
            return CONFIDENCE_HIGH, tuple(reasons), ()
        return CONFIDENCE_MEDIUM, tuple(reasons), ()

    def _no_action(self, row, need_type):
        if need_type == NEED_NONE:
            return NoActionScenario(
                current="Coverage appears adequate today.",
                short_term="Monitor the role for availability changes.",
                medium_term="No structural transfer action is currently required.",
            )
        return NoActionScenario(
            current=(
                "The current starter may remain adequate, but the squad keeps the identified planning risk."
            ),
            short_term=(
                "The role remains exposed if availability or form changes."
            ),
            medium_term=(
                "The structural gap remains unresolved without an internal successor or profile recruitment."
            ),
        )

    def _formation_relevance(self, evolution, role):
        affinity = getattr(evolution.identity_continuity, "key_contributors", ())
        if role == "Central Defense":
            return ("3-5-2", "4-5-1", "5-3-2")
        if role == "Midfield":
            return ("3-5-2", "4-5-1", "4-4-2")
        if role == "Winger":
            return ("3-5-2", "4-4-2", "5-4-1")
        if role == "Forward":
            return ("3-4-3", "4-3-3", "2-5-3")
        if role == "Goalkeeper":
            return ("All supported formations",)
        return tuple(affinity)[:3]

    def _identity_roles(self, identity):
        text = str(identity or "").lower()
        if "midfield" in text:
            return {"Midfield"}
        if "wing" in text or "band" in text:
            return {"Winger", "Wing Defense"}
        if "defensive" in text:
            return {"Central Defense", "Wing Defense", "Goalkeeper"}
        if "forward" in text or "attack" in text:
            return {"Forward", "Winger"}
        return set()

    def _rank(self, needs, constraints):
        objective_bonus = {
            OBJECTIVE_PROMOTION_PUSH: {
                NEED_IMMEDIATE_STARTER: 2,
                NEED_STARTER_COMPETITION: 1,
            },
            OBJECTIVE_LONG_TERM_DEVELOPMENT: {
                NEED_DEVELOPMENT_PROSPECT: 2,
                NEED_SUCCESSION_REPLACEMENT: 1,
            },
            OBJECTIVE_SQUAD_RENEWAL: {
                NEED_SUCCESSION_REPLACEMENT: 2,
                NEED_DEVELOPMENT_PROSPECT: 1,
            },
            OBJECTIVE_IMMEDIATE_STABILITY: {
                NEED_RELIABLE_BACKUP: 2,
                NEED_IMMEDIATE_STARTER: 1,
            },
        }.get(constraints.planning_objective, {})

        def key(need):
            return (
                -(
                    URGENCY_WEIGHT[need.urgency]
                    + objective_bonus.get(need.need_type, 0)
                    + (1 if need.structural_or_temporary == "structural" else 0)
                    + (1 if need.internal_solution_status == INTERNAL_NONE else 0)
                    + (1 if need.identity_relevance == "core_identity_support" else 0)
                ),
                need.structural_or_temporary != "structural",
                need.planning_horizon == HORIZON_MEDIUM_TERM,
                need.role.casefold(),
            )

        return sorted(needs, key=key)

    def _summary(self, needs, evolution, constraints):
        actionable = [need for need in needs if need.need_type != NEED_NONE]
        structural = [
            need for need in actionable if need.structural_or_temporary == "structural"
        ]
        development = [
            need for need in actionable if need.need_type == NEED_DEVELOPMENT_PROSPECT
        ]
        internal = [
            need for need in actionable
            if need.recommended_action == ACTION_DEVELOP_INTERNALLY
        ]
        critical_dependencies = [
            dependency for dependency in evolution.dependencies
            if dependency.dependency_level == RISK_CRITICAL
        ]
        top = actionable[0].role if actionable else ""
        if not actionable:
            sentences = ("No urgent transfer need detected.",)
        else:
            sentences = (
                f"Top transfer profile priority is {top}.",
                "Recommendations are profile-based and do not use live market data.",
            )
        return TransferPlanSummary(
            top_priority=top,
            structural_need_count=len(structural),
            development_need_count=len(development),
            internal_solution_count=len(internal),
            critical_dependency_count=len(critical_dependencies),
            selected_planning_objective=constraints.planning_objective,
            summary_sentences=sentences,
        )

    @staticmethod
    def _need_id(role):
        return str(role).lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _with_rank(need, rank):
        return TransferNeed(
            need_id=need.need_id,
            role=need.role,
            position_family=need.position_family,
            priority_rank=rank,
            urgency=need.urgency,
            planning_horizon=need.planning_horizon,
            need_type=need.need_type,
            target_squad_role=need.target_squad_role,
            reason_keys=need.reason_keys,
            source_risks=need.source_risks,
            structural_or_temporary=need.structural_or_temporary,
            internal_solution_status=need.internal_solution_status,
            training_support=need.training_support,
            identity_relevance=need.identity_relevance,
            formation_relevance=need.formation_relevance,
            recommended_action=need.recommended_action,
            recommended_profile=need.recommended_profile,
            alternative_profiles=need.alternative_profiles,
            impact_projection=need.impact_projection,
            confidence=need.confidence,
            confidence_reasons=need.confidence_reasons,
            data_limitations=need.data_limitations,
            no_action_scenario=need.no_action_scenario,
        )
