from engine.squad_evolution import SquadEvolutionAnalyzer
from engine.squad_evolution.catalogs import (
    PLANNING_HORIZONS,
    TRAINING_FOCUSES,
    normalize_horizon,
    normalize_training_focus,
)
from engine.squad_evolution.models import (
    HORIZON_CURRENT,
    TRAINING_UNKNOWN,
)
from ht_coach_app.services.squad_builder_service import (
    AVAILABILITY_CURRENT,
    AVAILABILITY_FULL_STRENGTH,
    AUTO_FORMATION,
    SquadBuilderService,
)


class SquadEvolutionService:
    def __init__(
        self,
        builder_service=None,
        analyzer=None,
    ):
        self._builder_service = builder_service or SquadBuilderService()
        self._analyzer = analyzer or SquadEvolutionAnalyzer()
        self._cache = {}

    def planning_horizons(self):
        return list(PLANNING_HORIZONS)

    def training_focuses(self):
        return list(TRAINING_FOCUSES)

    def normalize_horizon(self, value):
        return normalize_horizon(value)

    def normalize_training_focus(self, value):
        return normalize_training_focus(value)

    def analyze(
        self,
        players,
        planning_horizon=HORIZON_CURRENT,
        training_focus=TRAINING_UNKNOWN,
        full_strength_result=None,
        current_available_result=None,
    ):
        players = list(players or [])
        full_strength_result = full_strength_result or self._build_cached(
            players,
            AVAILABILITY_FULL_STRENGTH,
        )
        current_available_result = current_available_result or self._build_cached(
            players,
            AVAILABILITY_CURRENT,
        )
        return self._analyzer.analyze(
            players,
            full_strength_result=full_strength_result,
            current_available_result=current_available_result,
            planning_horizon=planning_horizon,
            training_focus=training_focus,
        )

    def clear_cache(self):
        self._cache.clear()

    def _build_cached(self, players, availability_mode):
        key = (
            availability_mode,
            tuple(
                (
                    getattr(player, "name", ""),
                    getattr(player, "age", None),
                    getattr(player, "days", None),
                    getattr(player, "injury", None),
                )
                for player in players
            ),
        )
        if key not in self._cache:
            self._cache[key] = self._builder_service.build(
                players,
                AUTO_FORMATION,
                availability_mode,
            )
        return self._cache[key]
