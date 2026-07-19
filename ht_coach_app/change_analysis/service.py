from dataclasses import asdict

from ht_coach_app.change_analysis.models import (
    ChangeAnalysisResult,
    ChangeSummary,
    ChangeValueDelta,
    LastChange,
    PositionFitChange,
)


SECTOR_LABELS = {
    "left_defense": "Left Defense",
    "central_defense": "Central Defense",
    "right_defense": "Right Defense",
    "midfield": "Midfield",
    "left_attack": "Left Attack",
    "central_attack": "Central Attack",
    "right_attack": "Right Attack",
}


class ChangeAnalysisService:
    PROBABILITY_EPSILON = 0.0005
    SECTOR_EPSILON = 0.005
    STRONG_SECTOR_DROP = 2.0

    def analyze(self, previous_result, current_result, workspace_state):
        modification = self._last_modification(workspace_state)
        if (
            previous_result is None
            or current_result is None
            or modification is None
        ):
            return None

        previous = self._formation_result(
            previous_result,
            modification.formation_name,
        )
        current = self._formation_result(
            current_result,
            modification.formation_name,
        )
        if previous is None or current is None:
            return None

        team_impact = self._team_impact(previous, current)
        sector_changes = self._sector_changes(previous, current)
        position_fit = PositionFitChange(
            previous_player_score=float(
                modification.previous_slot_score or 0.0
            ),
            current_player_score=float(
                modification.current_slot_score or 0.0
            ),
            difference=float(modification.score_difference),
        )

        return ChangeAnalysisResult(
            last_change=LastChange(
                incoming_player=modification.replacement_player_name,
                outgoing_player=modification.original_player_name,
                slot=modification.role,
                formation_name=modification.formation_name,
            ),
            position_fit=position_fit,
            team_impact=team_impact,
            sector_changes=sector_changes,
            summary=self._summary(team_impact, sector_changes),
        )

    def _team_impact(self, previous, current):
        values = [
            (
                "Win",
                previous.win_probability,
                current.win_probability,
            ),
            (
                "Draw",
                previous.draw_probability,
                current.draw_probability,
            ),
            (
                "Loss",
                previous.loss_probability,
                current.loss_probability,
            ),
        ]
        return [
            ChangeValueDelta(
                label=label,
                old_value=float(old),
                new_value=float(new),
                difference=float(new) - float(old),
                value_type="percent",
            )
            for label, old, new in values
        ]

    def _sector_changes(self, previous, current):
        changes = []
        previous_ratings = previous.team_ratings
        current_ratings = current.team_ratings

        for attribute, label in SECTOR_LABELS.items():
            old = float(getattr(previous_ratings, attribute, 0.0))
            new = float(getattr(current_ratings, attribute, 0.0))
            difference = new - old
            if abs(difference) <= self.SECTOR_EPSILON:
                continue
            changes.append(
                ChangeValueDelta(
                    label=label,
                    old_value=old,
                    new_value=new,
                    difference=difference,
                )
            )

        return changes

    def _summary(self, team_impact, sector_changes):
        win_delta = self._delta(team_impact, "Win")
        loss_delta = self._delta(team_impact, "Loss")
        strongest_sector_drop = min(
            [change.difference for change in sector_changes] or [0.0]
        )

        win_improved = win_delta > self.PROBABILITY_EPSILON
        loss_decreased = loss_delta < -self.PROBABILITY_EPSILON
        win_worse = win_delta < -self.PROBABILITY_EPSILON
        loss_worse = loss_delta > self.PROBABILITY_EPSILON
        strong_drop = strongest_sector_drop <= -self.STRONG_SECTOR_DROP
        any_sector_drop = any(
            change.difference < -self.SECTOR_EPSILON
            for change in sector_changes
        )

        if win_improved and loss_decreased and not strong_drop:
            return ChangeSummary(
                code="excellent_tradeoff",
                title_key="change.excellent_tradeoff",
                description_key="change.excellent_text",
            )
        if win_improved and not strong_drop:
            return ChangeSummary(
                code="balanced_improvement",
                title_key="change.balanced_improvement",
                description_key="change.balanced_text",
            )
        if (abs(win_delta) <= self.PROBABILITY_EPSILON and strong_drop) or (
            win_improved and any_sector_drop
        ):
            return ChangeSummary(
                code="risky_change",
                title_key="change.risky_change",
                description_key="change.risky_text",
            )
        if win_worse or loss_worse:
            return ChangeSummary(
                code="net_negative",
                title_key="change.net_negative",
                description_key="change.negative_text",
            )

        return ChangeSummary(
            code="balanced_improvement",
            title_key="change.balanced_improvement",
            description_key="change.balanced_text",
        )

    @staticmethod
    def _last_modification(workspace_state):
        history = tuple(getattr(workspace_state, "history", ()) or ())
        if not history:
            return None
        return history[-1]

    @staticmethod
    def _formation_result(result, formation_name):
        for formation in getattr(result, "formations", []) or []:
            if formation.formation_name == formation_name:
                return formation
        return None

    @staticmethod
    def _delta(team_impact, label):
        for change in team_impact:
            if change.label == label:
                return change.difference
        return 0.0


def change_analysis_result_to_dict(result):
    if result is None:
        return None
    return asdict(result)


def change_analysis_result_from_dict(data):
    if not isinstance(data, dict):
        return None

    try:
        summary = data.get("summary")
        return ChangeAnalysisResult(
            last_change=LastChange(
                incoming_player=data["last_change"].get(
                    "incoming_player",
                    "",
                ),
                outgoing_player=data["last_change"].get(
                    "outgoing_player",
                    "",
                ),
                slot=data["last_change"].get("slot", ""),
                formation_name=data["last_change"].get(
                    "formation_name",
                    "",
                ),
            ),
            position_fit=PositionFitChange(
                previous_player_score=float(
                    data["position_fit"].get("previous_player_score", 0.0)
                ),
                current_player_score=float(
                    data["position_fit"].get("current_player_score", 0.0)
                ),
                difference=float(data["position_fit"].get("difference", 0.0)),
            ),
            team_impact=[
                _value_delta_from_dict(item)
                for item in data.get("team_impact", [])
                if isinstance(item, dict)
            ],
            sector_changes=[
                _value_delta_from_dict(item)
                for item in data.get("sector_changes", [])
                if isinstance(item, dict)
            ],
            summary=(
                ChangeSummary(
                    code=summary.get("code", ""),
                    title_key=summary.get("title_key", ""),
                    description_key=summary.get("description_key", ""),
                )
                if isinstance(summary, dict)
                else None
            ),
            schema_version=int(data.get("schema_version", 1)),
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _value_delta_from_dict(data):
    return ChangeValueDelta(
        label=data.get("label", ""),
        old_value=float(data.get("old_value", 0.0)),
        new_value=float(data.get("new_value", 0.0)),
        difference=float(data.get("difference", 0.0)),
        value_type=data.get("value_type", "number"),
    )
