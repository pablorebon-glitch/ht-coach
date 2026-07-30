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

        if hasattr(self._view, "generate_requested"):
            self._view.generate_requested.connect(self._generate_report)
        if hasattr(self._view, "season_context_changed"):
            self._view.season_context_changed.connect(self._generate_report)

        self._view.show_empty_state()

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

    @classmethod
    def _format_sections(cls, report):
        status_text = (
            f"{t(project_status_label_key(report.project_status))}\n"
            f"{t('club_advisor.panel.confidence')}: {t(confidence_label_key(report.confidence))}"
        )

        strengths_text = (
            "\n".join(f"• {t(strength_label_key(s.strength_type))}" for s in report.strengths)
            or "-"
        )
        risks_text = (
            "\n".join(f"• {t(risk_label_key(r.risk_type))}" for r in report.risks) or "-"
        )
        warnings_text = (
            "\n".join(
                f"• {t(warning_label_key(w.warning_type))}: {t(w.reason_key, **w.reason_params)}"
                for w in report.warnings
            )
            or "-"
        )

        ts = report.training_summary
        training_text = (
            f"{t('club_advisor.panel.training.active_type')}: {ts.active_training_type or '-'}\n"
            f"{t('club_advisor.panel.training.primary_trainees')}: {ts.primary_trainee_count}\n"
            f"{t('club_advisor.panel.training.secondary_trainees')}: {ts.secondary_trainee_count}\n"
            f"{t('club_advisor.panel.training.without_training')}: {ts.players_without_training}"
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
