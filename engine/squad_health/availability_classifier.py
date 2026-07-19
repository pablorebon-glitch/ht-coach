from engine.squad_health.models import (
    AvailabilityRecord,
    AvailabilityStatus,
)


class AvailabilityClassifier:
    @staticmethod
    def classify(player):
        injury = getattr(player, "injury", None)
        raw = str(getattr(player, "injury_raw", "") or "").strip()

        if injury is None and raw:
            return AvailabilityRecord(
                player_id=AvailabilityClassifier._player_id(player),
                player_name=player.name,
                status=AvailabilityStatus.UNKNOWN,
                injury_value=None,
                eligible_for_selection=True,
                reason_key="availability.reason.unknown",
                severity="unknown",
                source_value=raw,
            )

        if injury is None:
            return AvailabilityRecord(
                player_id=AvailabilityClassifier._player_id(player),
                player_name=player.name,
                status=AvailabilityStatus.AVAILABLE,
                injury_value=None,
                eligible_for_selection=True,
                reason_key="availability.reason.available",
                severity="none",
                source_value=raw,
            )

        if float(injury) > 0:
            return AvailabilityRecord(
                player_id=AvailabilityClassifier._player_id(player),
                player_name=player.name,
                status=AvailabilityStatus.INJURED,
                injury_value=float(injury),
                eligible_for_selection=False,
                reason_key="availability.reason.injured",
                severity=AvailabilityClassifier._severity(float(injury)),
                estimated_absence_value=float(injury),
                source_value=raw,
            )

        return AvailabilityRecord(
            player_id=AvailabilityClassifier._player_id(player),
            player_name=player.name,
            status=AvailabilityStatus.AVAILABLE,
            injury_value=float(injury),
            eligible_for_selection=True,
            reason_key="availability.reason.available",
            severity="none",
            source_value=raw,
        )

    @staticmethod
    def _severity(injury):
        if injury >= 4:
            return "high"

        if injury >= 2:
            return "medium"

        return "low"

    @staticmethod
    def _player_id(player):
        return str(
            getattr(player, "id", "")
            or getattr(player, "player_id", "")
            or getattr(player, "name", "")
        )
