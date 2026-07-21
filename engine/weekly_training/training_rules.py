from decimal import Decimal

from engine.weekly_training.models import (
    PLAYMAKING,
    ExposureConfidence,
    TrainingCapacity,
    TrainingExposure,
)
from models.position import Position


class TrainingRuleProvider:
    training_type = ""

    def supports(self, training_type):
        return str(training_type or "").upper() == self.training_type

    def factor_for_position(self, position):
        raise NotImplementedError

    def exposure_for_entry(self, match_id, entry, source, confidence):
        factor = self.factor_for_position(entry.position)
        minutes = Decimal(str(entry.played_minutes))
        return TrainingExposure(
            player_id=entry.player_id,
            match_id=match_id,
            position_group=str(entry.position),
            played_minutes=minutes,
            training_factor=factor,
            effective_training_minutes=minutes * factor,
            source=source,
            confidence=confidence,
        )

    def capacity_for_formation(self, formation):
        full = 0
        half = 0
        for position, amount in formation.positions.items():
            factor = self.factor_for_position(position)
            if factor == Decimal("1"):
                full += int(amount)
            elif factor == Decimal("0.5"):
                half += int(amount)
        return TrainingCapacity(
            full_slots=full,
            half_slots=half,
            effective_player_equivalents=Decimal(full) + Decimal("0.5") * Decimal(half),
        )


class PlaymakingTrainingRules(TrainingRuleProvider):
    training_type = PLAYMAKING
    _FACTORS = {
        Position.INNER_MIDFIELDER.value: Decimal("1"),
        Position.WINGER.value: Decimal("0.5"),
    }

    def factor_for_position(self, position):
        value = getattr(position, "value", position)
        return self._FACTORS.get(str(value), Decimal("0"))


def rule_provider_for(training_type):
    provider = PlaymakingTrainingRules()
    if provider.supports(training_type):
        return provider
    return None


def assumed_confidence(minutes_known):
    return ExposureConfidence.CONFIRMED if minutes_known else ExposureConfidence.ASSUMED
