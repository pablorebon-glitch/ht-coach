from dataclasses import dataclass

from ht_coach_app.core.localization import t


FALLBACK_TEXTS = {
    "Translation unavailable",
    "Not available",
    "No disponible",
}

LITERAL_KEYS = {
    "role": {
        "Goalkeeper": "goalkeeper",
        "Central Defense": "central_defense",
        "Wing Defense": "wing_defense",
        "Midfield": "midfield",
        "Winger": "winger",
        "Forward": "forward",
    },
    "position": {
        "Goalkeeper": "goalkeeper",
        "Central Defender": "central_defender",
        "Wing Defender": "wing_defender",
        "Inner Midfielder": "inner_midfielder",
        "Winger": "winger",
        "Forward": "forward",
    },
    "target_role": {
        "Immediate Starter": "immediate_starter",
        "Starter Candidate": "starter_candidate",
        "Rotation Player": "rotation_player",
        "Reliable Backup": "reliable_backup",
        "Development Prospect": "development_prospect",
        "Specialist": "specialist",
        "No Transfer Needed": "no_transfer_needed",
    },
    "specialty": {
        "Header preferred": "header_preferred",
        "Quick optional": "quick_optional",
        "Technical optional": "technical_optional",
        "Unpredictable optional": "unpredictable_optional",
    },
    "formation": {
        "All supported formations": "all_supported",
    },
    "impact_dimension": {
        "Succession Risk": "succession_risk",
        "Dependency Risk": "dependency_risk",
        "Current Coverage": "current_coverage",
        "Formation Flexibility": "formation_flexibility",
        "Training Pipeline": "training_pipeline",
        "Age Balance": "age_balance",
    },
    "impact": {
        "No exact performance delta is projected for an abstract profile.": "no_exact_delta",
    },
    "tradeoff": {
        "Prioritizes immediate depth over optional versatility.": "immediate_depth",
        "Addresses structural risk before luxury upgrades.": "structural_risk",
        "May be less urgent once temporary availability improves.": "temporary_issue",
        "May not align strongly with the current training focus.": "training_focus",
    },
    "no_action": {
        "Coverage appears adequate today.": "coverage_adequate",
        "Monitor the role for availability changes.": "monitor_availability",
        "No structural transfer action is currently required.": "no_structural_action",
        "The current starter may remain adequate, but the squad keeps the identified planning risk.": "starter_may_hold",
        "The role remains exposed if availability or form changes.": "role_exposed",
        "The structural gap remains unresolved without an internal successor or profile recruitment.": "gap_unresolved",
    },
    "confidence_reason": {
        "Starter hierarchy and depth data are available.": "starter_depth_available",
    },
    "data_limitation": {
        "Starter age is unknown.": "starter_age_unknown",
        "Training focus is unknown.": "training_focus_unknown",
        "Full-strength starter hierarchy is incomplete.": "starter_hierarchy_incomplete",
    },
}


@dataclass(frozen=True)
class TransferNeedPresentation:
    summary: str
    profile: str
    why: str
    impact: str
    no_action: str
    alternatives: str
    technical: str


class TransferPlannerPresenter:
    def summary_lines(self, summary):
        top_priority = (
            self.translate_role(summary.top_priority)
            if summary.top_priority
            else "-"
        )
        lines = [
            t("transfer.top_priority_value", value=top_priority),
            t(
                "transfer.structural_needs_value",
                value=summary.structural_need_count,
            ),
            t(
                "transfer.development_needs_value",
                value=summary.development_need_count,
            ),
            t(
                "transfer.internal_solutions_value",
                value=summary.internal_solution_count,
            ),
            t(
                "transfer.critical_dependencies_value",
                value=summary.critical_dependency_count,
            ),
            t(
                "transfer.objective_value",
                value=self.translate_category(
                    "objective",
                    summary.selected_planning_objective,
                ),
            ),
        ]
        lines.extend(self.summary_sentences(summary))
        return lines

    def priority_row(self, need):
        return [
            need.priority_rank,
            self.translate_role(need.role),
            self.translate_category("urgency", need.urgency),
            self.translate_category("need_type", need.need_type),
            self.translate_target_role(need.target_squad_role),
            self.translate_category("action", need.recommended_action),
            self.translate_category(
                "internal",
                need.internal_solution_status,
            ),
        ]

    def need_presentation(self, need):
        return TransferNeedPresentation(
            summary=self.recommendation_summary(need),
            profile=self.recommended_profile(need),
            why=self.why_this_transfer(need),
            impact=self.expected_impact(need),
            no_action=self.no_action_scenario(need),
            alternatives=self.alternative_profiles(need.alternative_profiles),
            technical=self.technical_details(need),
        )

    def recommendation_summary(self, need):
        return "\n".join(
            self._rows(
                [
                    (t("transfer.field.position"), self.translate_role(need.role)),
                    (
                        t("transfer.field.urgency"),
                        self.translate_category("urgency", need.urgency),
                    ),
                    (
                        t("transfer.field.need_type"),
                        self.translate_category("need_type", need.need_type),
                    ),
                    (
                        t("transfer.field.action"),
                        self.translate_category("action", need.recommended_action),
                    ),
                    (
                        t("transfer.field.target_role"),
                        self.translate_target_role(need.target_squad_role),
                    ),
                    (
                        t("transfer.field.confidence"),
                        self.translate_category("confidence", need.confidence),
                    ),
                    (
                        t("transfer.field.planning_horizon"),
                        self.translate_evolution("horizon", need.planning_horizon),
                    ),
                ]
            )
        )

    def recommended_profile(self, need):
        profile = need.recommended_profile
        if profile is None:
            return t("transfer.no_profile_required")

        lines = self._rows(
            [
                (
                    t("transfer.field.position"),
                    self.translate_position(profile.position),
                ),
                (
                    t("transfer.field.target_role"),
                    self.translate_target_role(profile.target_role),
                ),
                (t("transfer.field.age_range"), profile.age_range),
                (
                    t("transfer.field.training_compatibility"),
                    self.translate_category(
                        "training_compatibility",
                        profile.training_compatibility,
                    ),
                ),
                (
                    t("transfer.field.formation_relevance"),
                    self.format_list(
                        self.translate_formation(item)
                        for item in profile.formation_compatibility
                    ),
                ),
                (
                    t("transfer.field.identity_fit"),
                    self.translate_category("identity", profile.identity_compatibility),
                ),
            ]
        )
        lines.extend(
            [
                "",
                t("transfer.field.primary_skill"),
                self._skill_requirement(profile.primary_skill),
                "",
                t("transfer.field.secondary_skills"),
                self.format_list(
                    self.translate_skill(skill.skill)
                    for skill in profile.secondary_skills
                ),
                "",
                t("transfer.field.optional_skills"),
                self.format_list(
                    self.translate_skill(skill)
                    for skill in profile.optional_skills
                ),
                "",
                t("transfer.field.specialty_preference"),
                self.format_list(
                    self.translate_specialty(specialty)
                    for specialty in profile.specialty_preferences
                ),
            ]
        )
        return "\n".join(lines)

    def why_this_transfer(self, need):
        reasons = []
        if need.structural_or_temporary == "structural":
            reasons.append(t("transfer.reason.structural_gap"))
        elif need.structural_or_temporary == "temporary":
            reasons.append(t("transfer.reason.temporary_issue"))
        if need.internal_solution_status == "no_internal_solution":
            reasons.append(t("transfer.reason.no_internal_solution"))
        elif need.internal_solution_status == "emergency_internal_cover_only":
            reasons.append(t("transfer.reason.emergency_cover"))
        elif need.internal_solution_status == "development_path_available":
            reasons.append(t("transfer.reason.development_path"))
        if need.training_support == "not_addressed":
            reasons.append(t("transfer.reason.training_pipeline_gap"))
        if need.identity_relevance == "core_identity_support":
            reasons.append(t("transfer.reason.identity_continuity"))
        if need.formation_relevance:
            reasons.append(
                t(
                    "transfer.reason.formation_support",
                    formations=self.format_list(
                        self.translate_formation(item)
                        for item in need.formation_relevance
                    ),
                )
            )
        for risk in need.source_risks:
            reasons.append(
                t(
                    "transfer.reason.source_risk",
                    risk=self.translate_evolution("risk", risk),
                )
            )
        return self.bullet_list(reasons)

    def expected_impact(self, need):
        impact = need.impact_projection
        return "\n".join(
            [
                *self._rows(
                    [
                        (
                            t("transfer.field.qualitative_impact"),
                            self.translate_category(
                                "impact",
                                impact.qualitative_impact,
                            ),
                        ),
                        (
                            t("transfer.field.training_effect"),
                            self.translate_evolution(
                                "alignment",
                                need.training_support,
                            ),
                        ),
                        (
                            t("transfer.field.identity_effect"),
                            self.translate_category(
                                "identity",
                                need.identity_relevance,
                            ),
                        ),
                    ]
                ),
                "",
                t("transfer.field.impact_dimensions"),
                self.bullet_list(
                    self.translate_impact_area(item)
                    for item in impact.dimensions
                ),
                "",
                self.translate_literal(
                    "impact",
                    impact.no_exact_delta_statement,
                ),
            ]
        )

    def no_action_scenario(self, need):
        scenario = need.no_action_scenario
        return "\n".join(
            self._rows(
                [
                    (
                        t("transfer.field.current_horizon"),
                        self.translate_literal("no_action", scenario.current),
                    ),
                    (
                        t("transfer.field.short_term"),
                        self.translate_literal("no_action", scenario.short_term),
                    ),
                    (
                        t("transfer.field.medium_term"),
                        self.translate_literal("no_action", scenario.medium_term),
                    ),
                ]
            )
        )

    def alternative_profiles(self, profiles):
        sections = []
        for index, profile in enumerate(profiles or (), start=1):
            tradeoff = (
                self.translate_literal("tradeoff", profile.tradeoffs[0])
                if profile.tradeoffs
                else t("common.not_available")
            )
            sections.append(
                "\n".join(
                    [
                        t(
                            "transfer.alternative_title",
                            index=index,
                            role=self.translate_target_role(profile.target_role),
                        ),
                        *self._rows(
                            [
                                (
                                    t("transfer.field.age_range"),
                                    profile.age_range,
                                ),
                                (
                                    t("transfer.field.primary_skill"),
                                    self.translate_skill(
                                        profile.primary_skill.skill
                                    ),
                                ),
                                (
                                    t("transfer.field.minimum"),
                                    self.translate_skill_level(
                                        profile.primary_skill.minimum_level
                                    ),
                                ),
                                (t("transfer.field.main_tradeoff"), tradeoff),
                            ]
                        ),
                    ]
                )
            )
        return "\n\n".join(sections) or t("transfer.no_alternatives")

    def technical_details(self, need):
        lines = []
        if need.confidence_reasons:
            lines.append(t("transfer.field.confidence_reasons"))
            lines.append(
                self.bullet_list(
                    self.translate_literal("confidence_reason", item)
                    for item in need.confidence_reasons
                )
            )
        if need.data_limitations:
            lines.append(t("transfer.field.data_limitations"))
            lines.append(
                self.bullet_list(
                    self.translate_literal("data_limitation", item)
                    for item in need.data_limitations
                )
            )
        return "\n".join(lines)

    def summary_sentences(self, summary):
        if not summary.top_priority:
            return [t("transfer.summary.no_urgent_need")]
        return [
            t(
                "transfer.summary.top_priority",
                value=self.translate_role(summary.top_priority),
            ),
            t("transfer.summary.profile_based"),
        ]

    def format_list(self, values):
        items = [
            str(value)
            for value in values
            if value not in {None, ""}
        ]
        if not items:
            return t("common.not_available")
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return t("common.list_two", first=items[0], second=items[1])
        return t(
            "common.list_many",
            items=", ".join(items[:-1]),
            last=items[-1],
        )

    def bullet_list(self, values):
        items = [
            str(value)
            for value in values
            if value not in {None, ""}
        ]
        if not items:
            return t("common.not_available")
        return "\n".join(f"- {item}" for item in items)

    def translate_role(self, value):
        return self.translate_literal("role", value)

    def translate_position(self, value):
        return self.translate_literal("position", value)

    def translate_target_role(self, value):
        return self.translate_literal("target_role", value)

    def translate_skill(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            return t("common.not_available")
        return self._localized_or_title(f"transfer.skill.{normalized}", normalized)

    def translate_skill_level(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            return t("common.not_available")
        return self._localized_or_title(
            f"transfer.skill_level.{normalized}",
            normalized,
        )

    def translate_specialty(self, value):
        literal = self.translate_literal("specialty", value)
        if literal != str(value or "").strip().replace("_", " ").title():
            return literal
        normalized = str(value or "").strip()
        return self._localized_or_title(f"transfer.specialty.{normalized}", normalized)

    def translate_impact_area(self, value):
        return self.translate_literal("impact_dimension", value)

    def translate_formation(self, value):
        return self.translate_literal("formation", value)

    def translate_evolution(self, category, value):
        normalized = str(value or "unknown").strip()
        return self._localized_or_title(
            f"evolution.{category}.{normalized}",
            normalized,
        )

    def translate_category(self, category, value):
        normalized = str(value or "unknown").strip()
        return self._localized_or_title(
            f"transfer.{category}.{normalized}",
            normalized,
        )

    def translate_literal(self, category, value):
        if value is None or value == "":
            return t("common.not_available")
        text = str(value).strip()
        literal_key = LITERAL_KEYS.get(category, {}).get(text)
        if literal_key:
            return self._localized_or_title(
                f"transfer.literal.{category}.{literal_key}",
                text,
            )
        return text.replace("_", " ").title()

    def _skill_requirement(self, requirement):
        return "\n".join(
            [
                self.translate_skill(requirement.skill),
                *self._rows(
                    [
                        (
                            t("transfer.field.minimum"),
                            self.translate_skill_level(
                                requirement.minimum_level
                            ),
                        ),
                        (
                            t("transfer.field.preferred"),
                            self.translate_skill_level(
                                requirement.preferred_level
                            ),
                        ),
                        (
                            t("transfer.field.stretch"),
                            self.translate_skill_level(
                                requirement.stretch_level
                            ),
                        ),
                    ]
                ),
            ]
        )

    def _rows(self, pairs):
        lines = []
        for label, value in pairs:
            lines.append(f"{label}:")
            lines.append(str(value or t("common.not_available")))
        return lines

    def _localized_or_title(self, key, fallback):
        value = t(key)
        if value in FALLBACK_TEXTS or value == key:
            return str(fallback or "").replace("_", " ").title()
        return value


def current_transfer_presenter():
    return TransferPlannerPresenter()
