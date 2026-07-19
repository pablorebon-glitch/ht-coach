from engine.squad_health.availability_classifier import AvailabilityClassifier
from engine.squad_health.models import AvailabilityStatus


CURRENT_AVAILABLE = "current_available"
FULL_STRENGTH = "full_strength"


class AvailabilityService:
    def __init__(self, classifier=AvailabilityClassifier):
        self._classifier = classifier

    def classify_roster(self, players):
        return [
            self._classifier.classify(player)
            for player in players
        ]

    def eligible_players(self, players, mode=CURRENT_AVAILABLE):
        if mode == FULL_STRENGTH:
            return list(players)

        records = {
            record.player_name: record
            for record in self.classify_roster(players)
        }
        return [
            player
            for player in players
            if records[player.name].eligible_for_selection
        ]

    def unavailable_records(self, players):
        return [
            record
            for record in self.classify_roster(players)
            if not record.eligible_for_selection
        ]

    def availability_by_name(self, players):
        return {
            record.player_name: record
            for record in self.classify_roster(players)
        }

    @staticmethod
    def normalize_mode(mode):
        if mode == FULL_STRENGTH:
            return FULL_STRENGTH

        return CURRENT_AVAILABLE

    @staticmethod
    def status_filter(record, selected):
        if not selected or selected == "all":
            return True

        if selected == "available":
            return record.eligible_for_selection

        if selected == "unavailable":
            return not record.eligible_for_selection

        if selected == "injured":
            return record.status == AvailabilityStatus.INJURED

        if selected == "unknown":
            return record.status == AvailabilityStatus.UNKNOWN

        return True
