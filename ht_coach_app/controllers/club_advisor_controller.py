from PySide6.QtCore import QObject

from ht_coach_app.core.localization import t
from ht_coach_app.services.club_advisor_formatting import (
    confidence_label_key,
    depth_status_label_key,
    limitation_label_key,
    priority_label_key,
    project_status_label_key,
    risk_label_key,
    strength_label_key,
    warning_label_key,
)
from ht_coach_app.services.club_advisor_presentation import (
    advisor_display_value,
    advisor_evidence_label,
    advisor_position_label,
    advisor_text,
    advisor_training_type_label,
)
from ht_coach_app.services.season_plan_formatting import (
    action_label_key,
    horizon_label_key,
    need_label_key,
    readiness_label_key,
    urgency_label_key,
)


def _not_available():
    return t("club_advisor.panel.not_available_detail")


def _message(key, params=None):
    return advisor_text(key, **(params or {})) if key else _not_available()


class ClubAdvisorController(QObject):
    def __init__(
        self,
        view,
        squad_service,
        settings_repository,
        club_advisor_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._view = view
        self._squad_service = squad_service
        self._settings_repository = settings_repository
        self._club_advisor_service = club_advisor_service

        self._last_report = None

        if hasattr(self._view, "generate_requested"):
            self._view.generate_requested.connect(self._generate_report)
        if hasattr(self._view, "season_context_changed"):
            self._view.season_context_changed.connect(self._generate_report)
        if hasattr(self._view, "card_clicked"):
            self._view.card_clicked.connect(self._open_drilldown)

        self._view.show_empty_state()

    def _open_drilldown(self, card_key):
        if self._last_report is None:
            return
        from ht_coach_app.widgets.drilldown_overlay import DrillDownOverlay

        builder = {
            "squad": self._squad_drilldown_rows,
            "training": self._training_drilldown_rows,
            "depth": self._depth_drilldown_rows,
            "risks": self._risks_drilldown_rows,
            "strengths": self._strengths_drilldown_rows,
            "limitations": self._limitations_drilldown_rows,
        }.get(card_key)
        if builder is None:
            return
        rows = builder(self._last_report)
        if not rows:
            return
        title = t(f"club_advisor.panel.{'section_' + card_key if card_key in ('squad', 'training') else card_key}")
        DrillDownOverlay.show_over(self._view, title, rows)

    @staticmethod
    def _squad_drilldown_rows(report):
        ss = report.squad_summary
        groups = (
            (t("club_advisor.panel.squad.key_starters"), ss.key_starter_players),
            (t("club_advisor.panel.squad.rotation"), ss.rotation_players),
            (t("club_advisor.panel.squad.development_projects"), ss.development_project_players),
            (t("club_advisor.panel.squad.transfer_candidates"), ss.transfer_candidate_players),
            (t("club_advisor.panel.squad.replaceable"), ss.replaceable_players),
            (t("club_advisor.panel.squad.veterans"), ss.veteran_players),
            (t("club_advisor.panel.squad.depth_players"), ss.depth_players),
        )
        rows = []
        for label, players in groups:
            if not players:
                continue
            player_list = ", ".join(players)
            detail = (
                f"{t('club_advisor.panel.explanation')}: {label}\n"
                f"{t('club_advisor.panel.players_involved')}: {player_list}\n"
                f"{t('club_advisor.panel.reason')}: "
                f"{t('club_advisor.panel.squad_group_reason')}\n"
                f"{t('club_advisor.panel.impact')}: "
                f"{t('club_advisor.panel.squad_group_impact')}\n"
                f"{t('club_advisor.panel.review')}: "
                f"{t('club_advisor.panel.review_roster_after_changes')}"
            )
            rows.append((f"{label} ({len(players)})", detail))
        return rows

    @staticmethod
    def _training_drilldown_rows(report):
        ts = report.training_summary
        active_training = (
            advisor_training_type_label(ts.active_training_type)
            if ts.active_training_type
            else _not_available()
        )
        rows = [
            (
                t("club_advisor.panel.training.active_type"),
                (
                    f"{t('club_advisor.panel.explanation')}: "
                    f"{t('club_advisor.panel.training.active_type')}\n"
                    f"{t('club_advisor.panel.reason')}: {active_training}\n"
                    f"{t('club_advisor.panel.review')}: "
                    f"{t('club_advisor.panel.review_weekly_training_plan')}"
                ),
            ),
        ]

        def _players_or_none(players):
            return ", ".join(players) if players else t("club_advisor.panel.no_players_in_group")

        rows.append(
            (
                "100%",
                (
                    f"{t('club_advisor.panel.explanation')}: 100%\n"
                    f"{t('club_advisor.panel.players_involved')}: "
                    f"{_players_or_none(ts.full_priority_players)}\n"
                    f"{t('club_advisor.panel.reason')}: "
                    f"{t('club_advisor.panel.training.full_effect_reason')}\n"
                    f"{t('club_advisor.panel.review')}: "
                    f"{t('club_advisor.panel.review_weekly_training_plan')}"
                ),
            )
        )
        rows.append(
            (
                "50%",
                (
                    f"{t('club_advisor.panel.explanation')}: 50%\n"
                    f"{t('club_advisor.panel.players_involved')}: "
                    f"{_players_or_none(ts.half_priority_players)}\n"
                    f"{t('club_advisor.panel.reason')}: "
                    f"{t('club_advisor.panel.training.half_effect_reason')}\n"
                    f"{t('club_advisor.panel.review')}: "
                    f"{t('club_advisor.panel.review_weekly_training_plan')}"
                ),
            )
        )
        rows.append(
            (
                t("club_advisor.panel.training.covered"),
                (
                    f"{t('club_advisor.panel.explanation')}: "
                    f"{t('club_advisor.panel.training.covered')}\n"
                    f"{t('club_advisor.panel.players_involved')}: "
                    f"{_players_or_none(ts.covered_players)}\n"
                    f"{t('club_advisor.panel.review')}: "
                    f"{t('club_advisor.panel.review_weekly_training_plan')}"
                ),
            )
        )
        if ts.uncovered_priority_players:
            rows.append(
                (
                    t("club_advisor.panel.training.uncovered"),
                    (
                        f"{t('club_advisor.panel.explanation')}: "
                        f"{t('club_advisor.panel.training.uncovered')}\n"
                        f"{t('club_advisor.panel.players_involved')}: "
                        f"{_players_or_none(ts.uncovered_priority_players)}\n"
                        f"{t('club_advisor.panel.reason')}: "
                        f"{t('club_advisor.panel.training.uncovered_reason')}\n"
                        f"{t('club_advisor.panel.review')}: "
                        f"{t('club_advisor.panel.review_weekly_training_plan')}"
                    ),
                )
            )
        if ts.players_without_training:
            rows.append(
                (
                    t("club_advisor.panel.training.no_training"),
                    (
                        f"{t('club_advisor.panel.explanation')}: "
                        f"{t('club_advisor.panel.training.no_training')}\n"
                        f"{t('club_advisor.panel.players_involved')}: "
                        f"{t('club_advisor.panel.training.players_count', count=ts.players_without_training)}\n"
                        f"{t('club_advisor.panel.reason')}: "
                        f"{t('club_advisor.panel.training.no_effect_reason')}\n"
                        f"{t('club_advisor.panel.review')}: "
                        f"{t('club_advisor.panel.review_weekly_training_plan')}"
                    ),
                )
            )

        warning_lines = "\n".join(
            f"{t(warning_label_key(w.warning_type))}: {_message(w.reason_key, w.reason_params)}"
            for w in report.warnings
            if w.warning_type.value
            in ("priority_trainees_missing_training", "training_slot_competition",
                "training_plan_deviation", "training_capacity_underused")
        )
        if warning_lines:
            rows.append((t("club_advisor.panel.warnings"), warning_lines))
        return rows

    @staticmethod
    def _depth_drilldown_rows(report):
        rows = []
        for item in report.depth_summary.positions:
            position = advisor_position_label(item.position)
            temporary = _not_available()
            if item.temporary_count is not None:
                temporary = (
                    f"{item.temporary_count} "
                    f"({t(depth_status_label_key(item.temporary_status))})"
                    if item.temporary_status
                    else str(item.temporary_count)
                )
            lines = [
                f"{t('club_advisor.panel.explanation')}: {position}",
                f"{t('club_advisor.panel.structural_status')}: {item.player_count}",
                f"{t('club_advisor.panel.temporary_availability')}: {temporary}",
                f"{t('club_advisor.panel.reason')}: {t(depth_status_label_key(item.status))}",
                f"{t('club_advisor.panel.impact')}: {t('club_advisor.panel.depth_impact')}",
                f"{t('club_advisor.panel.review')}: {t('club_advisor.panel.review_roster_after_changes')}",
            ]
            rows.append((position, "\n".join(lines)))
        return rows

    @staticmethod
    def _risks_drilldown_rows(report):
        rows = []
        for risk in report.risks:
            reason = _message(risk.reason_key, risk.reason_params)
            impact = t(f"club_advisor.impact.{risk.impact}") if risk.impact else _not_available()
            urgency = t(f"club_advisor.impact.{risk.urgency}") if risk.urgency else _not_available()
            review = t(risk.review_condition_key) if risk.review_condition_key else _not_available()
            affected = (
                ", ".join(risk.affected_players)
                if risk.affected_players
                else t("club_advisor.panel.no_players_involved")
            )
            detail = (
                f"{t('club_advisor.panel.explanation')}: {t(risk_label_key(risk.risk_type))}\n"
                f"{t('club_advisor.panel.reason')}: {reason}\n"
                f"{t('club_advisor.panel.impact')}: {impact}\n"
                f"{t('club_advisor.panel.urgency')}: {urgency}\n"
                f"{t('club_advisor.panel.affected_players')}: {affected}\n"
                f"{t('club_advisor.panel.review')}: {review}"
            )
            rows.append((t(risk_label_key(risk.risk_type)), detail))
        return rows

    @staticmethod
    def _strengths_drilldown_rows(report):
        rows = []
        for strength in report.strengths:
            evidence_lines = "; ".join(
                f"{advisor_evidence_label(item.label_key or item.evidence_type)}: "
                f"{advisor_display_value(item.value)}"
                for item in strength.evidence
            ) or _not_available()
            label = t(strength_label_key(strength.strength_type))
            detail = (
                f"{t('club_advisor.panel.explanation')}: {label}\n"
                f"{t('club_advisor.panel.reason')}: {evidence_lines}\n"
                f"{t('club_advisor.panel.impact')}: {t('club_advisor.panel.strength_impact')}\n"
                f"{t('club_advisor.panel.review')}: "
                f"{t('club_advisor.panel.review_roster_after_changes')}"
            )
            rows.append((label, detail))
        return rows

    @staticmethod
    def _limitations_drilldown_rows(report):
        rows = []
        for limitation in report.limitations:
            label = t(limitation_label_key(limitation))
            rows.append(
                (
                    label,
                    (
                        f"{t('club_advisor.panel.explanation')}: {label}\n"
                        f"{t('club_advisor.panel.reason')}: "
                        f"{t('club_advisor.drilldown.future_integration_note')}\n"
                        f"{t('club_advisor.panel.impact')}: "
                        f"{t('club_advisor.panel.limitation_impact')}\n"
                        f"{t('club_advisor.panel.review')}: "
                        f"{t('club_advisor.panel.review_roster_after_changes')}"
                    ),
                )
            )
        return rows

    def _load_players(self):
        settings = self._settings_repository.load()
        if not settings.players_csv_path:
            return None
        try:
            roster = self._squad_service.load_roster(settings.players_csv_path)
        except Exception:
            return None
        return roster.players if roster else None

    def _build_season_context(self):
        from engine.club_advisor.enums import (
            CurrentCompetitiveness,
            PromotionObjective,
            SeasonPhase,
        )
        from engine.club_advisor.season_context import SeasonContext

        if not hasattr(self._view, "season_context_values"):
            return SeasonContext()

        values = self._view.season_context_values()
        return SeasonContext(
            season_phase=SeasonPhase(values.get("season_phase", "unknown")),
            promotion_objective=PromotionObjective(
                values.get("promotion_objective", "welcome_if_natural")
            ),
            current_competitiveness=CurrentCompetitiveness(
                values.get("current_competitiveness", "unknown")
            ),
            bot_opponent_count=values.get("bot_opponent_count") or None,
            recent_major_signing=bool(values.get("recent_major_signing")),
            notes=values.get("notes", ""),
        )

    def _generate_report(self):
        players = self._load_players()
        if not players:
            self._view.show_empty_state()
            return

        if self._club_advisor_service is None:
            from ht_coach_app.services.club_advisor_service import ClubAdvisorAppService

            self._club_advisor_service = ClubAdvisorAppService()

        season_context = self._build_season_context()
        report = self._club_advisor_service.generate_report(players, season_context=season_context)
        self._last_report = report
        sections = self._format_sections(report)
        self._view.show_report(sections)

    @staticmethod
    def _format_priority_line(priority):
        need = t(need_label_key(priority.strategic_need)) if priority.strategic_need else _not_available()
        urgency = (
            t(urgency_label_key(priority.operational_urgency))
            if priority.operational_urgency
            else _not_available()
        )
        action = t(action_label_key(priority.action_type)) if priority.action_type else _not_available()
        horizon = (
            t(horizon_label_key(priority.recommendation_horizon))
            if priority.recommendation_horizon
            else _not_available()
        )
        reason = _message(priority.reason_key, priority.reason_params) if priority.reason_key else ""
        return (
            f"{t(priority_label_key(priority.priority_type))}\n"
            f"  {t('club_advisor.panel.need')}: {need} | "
            f"{t('club_advisor.panel.urgency')}: {urgency}\n"
            f"  {t('club_advisor.panel.action')}: {action} | "
            f"{t('club_advisor.panel.review')}: {horizon}\n"
            f"  {t('club_advisor.panel.reason')}: {reason}"
        )

    @classmethod
    def _format_priority_list(cls, priorities):
        return "\n\n".join(cls._format_priority_line(p) for p in priorities) or _not_available()

    @staticmethod
    def _format_promotion_readiness(assessment):
        if assessment is None:
            return _not_available()
        readiness_text = t(readiness_label_key(assessment.readiness))
        reason_text = _message(assessment.reason_key, assessment.reason_params) if assessment.reason_key else ""
        confidence_text = t(confidence_label_key(assessment.confidence))
        limitations_text = ", ".join(
            t(limitation_label_key(item)) for item in assessment.limitations
        )
        lines = [
            readiness_text,
            reason_text,
            f"{t('club_advisor.panel.confidence')}: {confidence_text}",
        ]
        if limitations_text:
            lines.append(f"{t('club_advisor.panel.limitations')}: {limitations_text}")
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _format_status_section(report):
        lines = [
            f"{t(project_status_label_key(report.project_status))}\n"
            f"{t('club_advisor.panel.confidence')}: {t(confidence_label_key(report.confidence))}"
        ]
        explanation = report.status_explanation
        if explanation is not None and explanation.reason_key:
            dimension_labels = ", ".join(
                t(f"club_advisor.status_dimension.{name}")
                for name in explanation.driving_dimensions
            ) or _not_available()
            lines.append(
                f"{t('club_advisor.panel.structural_status')}: "
                f"{t(project_status_label_key(explanation.structural_status))}\n"
                f"{t('club_advisor.panel.driven_by')}: {dimension_labels}\n"
                f"{t('club_advisor.panel.operational_status')}: "
                f"{t('club_advisor.operational_status.' + explanation.operational_status)}"
            )
            lines.append(
                f"{t('club_advisor.panel.reason')}: "
                f"{_message(explanation.reason_key, explanation.reason_params)}"
            )
        causes = []
        for risk in report.risks[:3]:
            label = t(risk_label_key(risk.risk_type))
            reason = _message(risk.reason_key, risk.reason_params) if risk.reason_key else ""
            urgency = t(f"club_advisor.impact.{risk.urgency}") if risk.urgency else ""
            suffix = f" ({t('club_advisor.panel.urgency')}: {urgency})" if urgency else ""
            causes.append(f"{label}: {reason}{suffix}" if reason else f"{label}{suffix}")
        for warning in report.warnings[:2]:
            label = t(warning_label_key(warning.warning_type))
            reason = _message(warning.reason_key, warning.reason_params)
            causes.append(f"{label}: {reason}")
        if causes:
            lines.append(f"{t('club_advisor.panel.causes')}\n" + "\n".join(causes))
        return "\n\n".join(lines)

    @staticmethod
    def _format_risks_list(risks):
        if not risks:
            return _not_available()
        blocks = []
        for risk in risks:
            reason = _message(risk.reason_key, risk.reason_params) if risk.reason_key else ""
            affected = (
                ", ".join(risk.affected_players)
                if risk.affected_players
                else t("club_advisor.panel.no_players_involved")
            )
            impact = t(f"club_advisor.impact.{risk.impact}") if risk.impact else _not_available()
            urgency = t(f"club_advisor.impact.{risk.urgency}") if risk.urgency else _not_available()
            review = t(risk.review_condition_key) if risk.review_condition_key else _not_available()
            blocks.append(
                f"{t(risk_label_key(risk.risk_type))}\n"
                f"  {t('club_advisor.panel.reason')}: {reason}\n"
                f"  {t('club_advisor.panel.impact')}: {impact} | "
                f"{t('club_advisor.panel.urgency')}: {urgency}\n"
                f"  {t('club_advisor.panel.affected_players')}: {affected}\n"
                f"  {t('club_advisor.panel.review')}: {review}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _format_warnings_list(warnings):
        return (
            "\n".join(
                f"{t(warning_label_key(w.warning_type))}: {_message(w.reason_key, w.reason_params)}"
                for w in warnings
            )
            or _not_available()
        )

    @classmethod
    def _format_sections(cls, report):
        status_text = cls._format_status_section(report)

        strengths_text = (
            "\n".join(t(strength_label_key(s.strength_type)) for s in report.strengths)
            or _not_available()
        )
        risks_text = cls._format_risks_list(report.risks)
        warnings_text = cls._format_warnings_list(report.warnings)

        ts = report.training_summary
        training_text = (
            f"{t('club_advisor.panel.training.active_type')}\n"
            f"{advisor_training_type_label(ts.active_training_type) if ts.active_training_type else _not_available()}\n\n"
            f"100%\n"
            f"{t('club_advisor.panel.training.players_count', count=ts.primary_trainee_count)}\n\n"
            f"50%\n"
            f"{t('club_advisor.panel.training.players_count', count=ts.secondary_trainee_count)}\n\n"
            f"{t('club_advisor.panel.training.no_training')}\n"
            f"{t('club_advisor.panel.training.players_count', count=ts.players_without_training)}"
        )

        ss = report.squad_summary
        squad_text = (
            f"{t('club_advisor.panel.squad.key_starters')}: {ss.key_starter_count}\n"
            f"{t('club_advisor.panel.squad.rotation')}: {ss.rotation_count}\n"
            f"{t('club_advisor.panel.squad.development_projects')}: {ss.development_project_count}\n"
            f"{t('club_advisor.panel.squad.transfer_candidates')}: {ss.transfer_candidate_count}\n"
            f"{t('club_advisor.panel.squad.replaceable')}: {ss.replaceable_count}\n"
            f"{t('club_advisor.panel.squad.veterans')}: {ss.veteran_count}\n"
            f"{t('club_advisor.panel.squad.depth_players')}: {ss.depth_player_count}"
        )

        depth_text = "\n".join(
            f"{advisor_position_label(item.position)}: "
            f"{t(depth_status_label_key(item.status))} ({item.player_count})"
            for item in report.depth_summary.positions
        )

        limitations_text = (
            "\n".join(t(limitation_label_key(item)) for item in report.limitations)
            or _not_available()
        )

        return {
            "status": status_text,
            "operational": cls._format_priority_list(report.operational_priorities),
            "strategic": cls._format_priority_list(report.strategic_priorities),
            "promotion_readiness": cls._format_promotion_readiness(report.promotion_readiness),
            "strengths": strengths_text,
            "risks": risks_text,
            "training": training_text,
            "squad": squad_text,
            "depth": depth_text,
            "warnings": warnings_text,
            "limitations": limitations_text,
        }
