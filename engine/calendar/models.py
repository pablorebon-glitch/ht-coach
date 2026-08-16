from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from engine.calendar.enums import HTWeekState, HTWeekday


@dataclass(frozen=True)
class HTWeekSnapshot:
    """Everything a caller needs to know about "what week is this?" --
    every future module (Training, History, Finance, Advisor, Match
    Intelligence, Evolution) reads this instead of doing its own
    datetime arithmetic."""

    reference_time: datetime
    weekday: HTWeekday
    state: HTWeekState
    training_week_id: str
    training_processed: bool
    league_match_played: bool
    friendly_played: bool
    financial_update_completed: bool
    youth_scout_completed: bool
    days_until_training: int
    days_until_finances: int
    days_until_match: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_time": self.reference_time.isoformat(),
            "weekday": self.weekday.value,
            "state": self.state.value,
            "training_week_id": self.training_week_id,
            "training_processed": self.training_processed,
            "league_match_played": self.league_match_played,
            "friendly_played": self.friendly_played,
            "financial_update_completed": self.financial_update_completed,
            "youth_scout_completed": self.youth_scout_completed,
            "days_until_training": self.days_until_training,
            "days_until_finances": self.days_until_finances,
            "days_until_match": self.days_until_match,
        }


@dataclass(frozen=True)
class FinancialWeekSnapshot:
    """Part 4: a reusable contract for a future Finance module --
    intentionally *not* implemented here. No calculation lives in this
    sprint; every numeric field defaults to `None` (unknown) rather
    than a fabricated zero, so a consumer can tell "not computed yet"
    apart from "genuinely zero"."""

    week_id: str = ""
    balance: float | None = None
    income: float | None = None
    expenses: float | None = None
    salary: float | None = None
    maintenance: float | None = None
    interest: float | None = None
    cash_flow: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "week_id": self.week_id,
            "balance": self.balance,
            "income": self.income,
            "expenses": self.expenses,
            "salary": self.salary,
            "maintenance": self.maintenance,
            "interest": self.interest,
            "cash_flow": self.cash_flow,
        }


@dataclass(frozen=True)
class YouthWeekSnapshot:
    """Part 5: a reusable contract for a future Youth module --
    intentionally *not* implemented here, same discipline as
    `FinancialWeekSnapshot`."""

    week_id: str = ""
    recruitment_completed: bool | None = None
    recruitment_date: date | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "week_id": self.week_id,
            "recruitment_completed": self.recruitment_completed,
            "recruitment_date": (
                self.recruitment_date.isoformat() if self.recruitment_date else None
            ),
            "notes": self.notes,
        }
