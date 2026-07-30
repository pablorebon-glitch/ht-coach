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
from ht_coach_app.services.season_plan_formatting import (
    action_label_key,
    horizon_label_key,
    need_label_key,
    readiness_label_key,
    urgency_label_key,
)


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
            detail = "\n".join(f"• {name}" for name in players)
            rows.append((f"{label} ({len(players)})", detail))
        return rows

    @staticmethod
    def _training_drilldown_rows(report):
        ts = report.training_summary
        rows = [
            (
                t("club_advisor.panel.training.active_type"),
                ts.active_training_type or "-",
            ),
            (
                "100%",
                str(ts.primary_trainee_count),
            ),
            (
                "50%",
                str(ts.secondary_trainee_count),
            ),
            (
                "No training",
                str(ts.players_without_training),
            ),
        ]
        warning_lines = "\n".join(
            f"• {t(warning_label_key(w.warning_type))}: {t(w.reason_key, **w.reason_params)}"
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
            lines = [
                f"{t('club_advisor.panel.depth')}: {t(depth_status_label_key(item.status))}",
                f"{t('club_advisor.panel.structural_status')}: {item.player_count}",
            ]
            if item.temporary_count is not None:
                lines.append(
                    f"{t('club_advisor.panel.temporary_availability')}: "
                    f"{item.temporary_count} "
                    f"({t(depth_status_label_key(item.temporary_status))})"
                    if item.temporary_status
                    else f"{t('club_advisor.panel.temporary_availability')}: {item.temporary_count}"
                )
            rows.append((item.position, "\n".join(lines)))
        return rows

    @staticmethod
    def _risks_drilldown_rows(report):
        rows = []
        for risk in report.risks:
            reason = t(risk.reason_key, **risk.reason_params) if risk.reason_key else "-"
            impact = t(f"club_advisor.impact.{risk.impact}") if risk.impact else "-"
            urgency = t(f"club_advisor.impact.{risk.urgency}") if risk.urgency else "-"
            review = t(risk.review_condition_key) if risk.review_condition_key else "-"
            affected = ", ".join(risk.affected_players) if risk.affected_players else "-"
            detail = (
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
            evidence_lines = "\n".join(
                f"• {item.label_key or item.evidence_type}: {item.value}"
                for item in strength.evidence
            ) or "-"
            rows.append((t(strength_label_key(strength.strength_type)), evidence_lines))
        return rows

    @staticmethod
    def _limitations_drilldown_rows(report):
        rows = []
        for limitation in report.limitations:
            rows.append(
                (
                    t(limitation_label_key(limitation)),
                    t("club_advisor.drilldown.future_integration_note"),
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
        need = t(need_label_key(priority.strategic_need)) if priority.strategic_need else "-"
        urgency = (
            t(urgency_label_key(priority.operational_urgency))
            if priority.operational_urgency
            else "-"
        )
        action = t(action_label_key(priority.action_type)) if priority.action_type else "-"
        horizon = (
            t(horizon_label_key(priority.recommendation_horizon))
            if priority.recommendation_horizon
            else "-"
        )
        reason = t(priority.reason_key, **priority.reason_params) if priority.reason_key else ""
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
        return "\n\n".join(cls._format_priority_line(p) for p in priorities) or "-"

    @staticmethod
    def _format_promotion_readiness(assessment):
        if assessment is None:
            return "-"
        readiness_text = t(readiness_label_key(assessment.readiness))
        reason_text = t(assessment.reason_key, **assessment.reason_params) if assessment.reason_key else ""
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
            ) or "-"
            lines.append(
                f"{t('club_advisor.panel.structural_status')}: "
                f"{t(project_status_label_key(explanation.structural_status))}\n"
                f"{t('club_advisor.panel.driven_by')}: {dimension_labels}\n"
                f"{t('club_advisor.panel.operational_status')}: "
                f"{t('club_advisor.operational_status.' + explanation.operational_status)}"
            )
            lines.append(
                f"{t('club_advisor.panel.reason')}: "
                f"{t(explanation.reason_key, **explanation.reason_params)}"
            )
        causes = []
        for risk in report.risks[:3]:
            label = t(risk_label_key(risk.risk_type))
            reason = t(risk.reason_key, **risk.reason_params) if risk.reason_key else ""
            causes.append(f"- {label}: {reason}" if reason else f"- {label}")
        for warning in report.warnings[:2]:
            label = t(warning_label_key(warning.warning_type))
            reason = t(warning.reason_key, **warning.reason_params)
            causes.append(f"- {label}: {reason}")
        if causes:
            lines.append("Reasons\n" + "\n".join(causes))
        return "\n\n".join(lines)

    @staticmethod
    def _format_risks_list(risks):
        if not risks:
            return "-"
        blocks = []
        for risk in risks:
            reason = t(risk.reason_key, **risk.reason_params) if risk.reason_key else ""
            affected = ", ".join(risk.affected_players) if risk.affected_players else "-"
            impact = t(f"club_advisor.impact.{risk.impact}") if risk.impact else "-"
            urgency = t(f"club_advisor.impact.{risk.urgency}") if risk.urgency else "-"
            review = t(risk.review_condition_key) if risk.review_condition_key else "-"
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
                f"• {t(warning_label_key(w.warning_type))}: {t(w.reason_key, **w.reason_params)}"
                for w in warnings
            )
            or "-"
        )

    @classmethod
    def _format_sections(cls, report):
        status_text = cls._format_status_section(report)

        strengths_text = (
            "\n".join(f"• {t(strength_label_key(s.strength_type))}" for s in report.strengths)
            or "-"
        )
        risks_text = cls._format_risks_list(report.risks)
        warnings_text = cls._format_warnings_list(report.warnings)

        ts = report.training_summary
        training_text = (
            f"{t('club_advisor.panel.training.active_type')}\n"
            f"{ts.active_training_type or '-'}\n\n"
            f"100%\n{ts.primary_trainee_count} players\n\n"
            f"50%\n{ts.secondary_trainee_count} players\n\n"
            f"No training\n{ts.players_without_training} players"
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
            f"{item.position}: {t(depth_status_label_key(item.status))} ({item.player_count})"
            for item in report.depth_summary.positions
        )

        limitations_text = (
            "\n".join(f"• {t(limitation_label_key(item))}" for item in report.limitations) or "-"
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
