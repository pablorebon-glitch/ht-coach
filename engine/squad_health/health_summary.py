from engine.squad_health.models import (
    CoverageResult,
    HealthSummaryResult,
    UnavailablePlayer,
)


class HealthSummaryBuilder:
    ROLE_POSITIONS = {
        "Goalkeeper": "Goalkeeper",
        "Central Defense": "Central Defender",
        "Wing Defense": "Wing Back",
        "Midfield": "Inner Midfielder",
        "Winger": "Winger",
        "Forward": "Forward",
    }

    def build(
        self,
        players,
        eligible_players,
        availability_records,
        player_details_by_name,
        mode_label,
        impact=None,
    ):
        unavailable = [
            record
            for record in availability_records
            if not record.eligible_for_selection
        ]
        unavailable_players = tuple(
            UnavailablePlayer(
                player_name=record.player_name,
                status_label=record.status.value,
                injury_value=self._injury_label(record.injury_value),
                best_position=self._best_position(
                    player_details_by_name,
                    record.player_name,
                ),
                expected_role="Starting XI" if record.player_name in self._starter_names(impact) else "Depth",
            )
            for record in unavailable
        )
        coverage = tuple(
            self._coverage_for_role(role, position, eligible_players, player_details_by_name)
            for role, position in self.ROLE_POSITIONS.items()
        )
        affected_areas = tuple(
            result.role
            for result in coverage
            if result.classification != "Healthy"
        )

        return HealthSummaryResult(
            mode_label=mode_label,
            available_count=len(eligible_players),
            total_count=len(players),
            unavailable_starters=sum(
                1
                for player in unavailable_players
                if player.expected_role == "Starting XI"
            ),
            affected_areas=affected_areas,
            severity=self._severity(coverage, unavailable),
            unavailable_players=unavailable_players,
            coverage=coverage,
            impact=impact,
        )

    @staticmethod
    def _injury_label(value):
        if value is None:
            return ""

        if float(value).is_integer():
            return str(int(value))

        return f"{float(value):.1f}"

    @staticmethod
    def _best_position(details_by_name, player_name):
        detail = details_by_name.get(player_name)
        if detail is None:
            return ""

        return detail.player.best_position

    @staticmethod
    def _starter_names(impact):
        if impact is None:
            return set()

        return set(
            getattr(impact, "unavailable_starter_names", ())
        )

    def _coverage_for_role(
        self,
        role,
        position,
        eligible_players,
        player_details_by_name,
    ):
        candidates = [
            detail
            for detail in player_details_by_name.values()
            if detail is not None
            and any(
                position in ranking[0]
                for ranking in detail.rankings
            )
            and any(player.name == detail.player.name for player in eligible_players)
        ]
        candidates.sort(
            key=lambda detail: max(
                (
                    score
                    for label, score, _rank in detail.rankings
                    if position in label
                ),
                default=0.0,
            ),
            reverse=True,
        )

        if not candidates:
            classification = "Critical"
            starter = ""
        elif len(candidates) == 1:
            classification = "Limited"
            starter = candidates[0].player.name
        else:
            classification = "Healthy"
            starter = candidates[0].player.name

        return CoverageResult(
            role=role,
            classification=classification,
            starter=starter,
            eligible_alternatives=max(0, len(candidates) - 1),
        )

    @staticmethod
    def _severity(coverage, unavailable):
        if any(item.classification == "Critical" for item in coverage):
            return "High"

        if unavailable or any(item.classification == "Limited" for item in coverage):
            return "Medium"

        return "Low"
