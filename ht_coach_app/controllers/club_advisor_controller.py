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

    def _generate_report(self):
        players = self._load_players()
        if not players:
            self._view.show_empty_state()
            return

        if self._club_advisor_service is None:
            from ht_coach_app.services.club_advisor_service import ClubAdvisorAppService

            self._club_advisor_service = ClubAdvisorAppService()

        report = self._club_advisor_service.generate_report(players)
        sections = self._format_sections(report)
        self._view.show_report(sections)

    @staticmethod
    def _format_sections(report):
        status_text = (
            f"{t(project_status_label_key(report.project_status))}\n"
            f"{t('club_advisor.panel.confidence')}: {t(confidence_label_key(report.confidence))}"
        )

        if report.priorities:
            priorities_text = "\n".join(
                f"{p.rank}. {t(priority_label_key(p.priority_type))}" for p in report.priorities
            )
        else:
            priorities_text = "-"

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
            "priorities": priorities_text,
            "strengths": strengths_text,
            "risks": risks_text,
            "training": training_text,
            "squad": squad_text,
            "depth": depth_text,
            "warnings": warnings_text,
            "limitations": limitations_text,
        }
