from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Iterator

from engine.rating_validation.exceptions import DuplicateFixtureError
from engine.rating_validation.fixture import FixtureCompleteness, RatingValidationFixture


@dataclass(frozen=True)
class RatingValidationDataset:
    fixtures: tuple[RatingValidationFixture, ...] = ()

    def __post_init__(self):
        seen: set[str] = set()
        for fixture in self.fixtures:
            identifier = fixture.identifier
            if identifier in seen:
                raise DuplicateFixtureError(f"duplicate fixture identifier: {identifier}")
            seen.add(identifier)

    @classmethod
    def from_fixtures(
        cls,
        fixtures: Iterable[RatingValidationFixture],
    ) -> "RatingValidationDataset":
        return cls(tuple(fixtures))

    def __iter__(self) -> Iterator[RatingValidationFixture]:
        return iter(self.fixtures)

    def __len__(self) -> int:
        return len(self.fixtures)

    def count(self) -> int:
        return len(self.fixtures)

    def filter(
        self,
        predicate: Callable[[RatingValidationFixture], bool],
    ) -> "RatingValidationDataset":
        return RatingValidationDataset.from_fixtures(
            fixture for fixture in self.fixtures if predicate(fixture)
        )

    def by_completeness(
        self,
        completeness: FixtureCompleteness | str,
    ) -> "RatingValidationDataset":
        requested = (
            completeness
            if isinstance(completeness, FixtureCompleteness)
            else FixtureCompleteness(str(completeness))
        )
        return self.filter(
            lambda fixture: fixture.classified_completeness == requested
        )

    def group_by_completeness(self) -> dict[FixtureCompleteness, tuple[RatingValidationFixture, ...]]:
        groups = {completeness: [] for completeness in FixtureCompleteness}
        for fixture in self.fixtures:
            groups[fixture.classified_completeness].append(fixture)
        return {key: tuple(value) for key, value in groups.items()}
