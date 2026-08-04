"""Persistence for the HT Season Calendar configuration (Alpha 0.6.7 HF-02,
Part 11).
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone

from engine.calendar.season_calendar import SeasonCalendarConfig


class SeasonCalendarRepository:
    def __init__(self, storage_path):
        self.storage_path = storage_path

    def load(self):
        if not self.storage_path.exists():
            return SeasonCalendarConfig()
        with open(self.storage_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return SeasonCalendarConfig.from_dict(data)

    def save(self, config):
        if not getattr(config, "updated_at", ""):
            config = replace(
                config,
                updated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(config.to_dict(), file, indent=2)
        return config
