import csv
from dataclasses import dataclass, fields
from pathlib import Path

from engine.analyzers.player_analyzer import PlayerAnalyzer
from ht_coach_app.core.position_formatting import (
    format_position,
    normalize_position_value,
)
from models.position import Position


SUPPORTED_POSITIONS = {
    format_position(Position.GOALKEEPER): Position.GOALKEEPER.value,
    format_position(Position.CENTRAL_DEFENDER): Position.CENTRAL_DEFENDER.value,
    format_position(Position.WING_BACK): Position.WING_BACK.value,
    format_position(Position.INNER_MIDFIELDER): Position.INNER_MIDFIELDER.value,
    format_position(Position.WINGER): Position.WINGER.value,
    format_position(Position.FORWARD): Position.FORWARD.value,
}


class SquadValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PlayerRow:
    name: str
    age: int
    form: int
    stamina: int
    experience: int
    leadership: int
    tsi: int
    salary: int
    goalkeeper: int
    defending: int
    playmaking: int
    winger: int
    passing: int
    scoring: int
    set_pieces: int
    speciality: str
    selected_position_score: float = 0.0
    selected_position_rank: int = 0
    best_position: str = ""
    best_position_score: float = 0.0


@dataclass(frozen=True)
class PlayerDetail:
    player: PlayerRow
    rankings: list[tuple[str, float, int]]


@dataclass(frozen=True)
class RosterResult:
    players: list[object]
    rows: list[PlayerRow]
    source_path: str

    @property
    def player_count(self):
        return len(self.players)

    @property
    def specialties(self):
        values = {
            row.speciality
            for row in self.rows
            if row.speciality
        }
        return sorted(values)


class SquadService:
    def __init__(
        self,
        importer=None,
        analyzer=PlayerAnalyzer
    ):
        self._importer = importer
        self._analyzer = analyzer

    def supported_positions(self):
        return list(SUPPORTED_POSITIONS.keys())

    def load_roster(self, csv_path):
        normalized_path = str(csv_path).strip()

        if not normalized_path:
            raise SquadValidationError(
                "Select a players CSV file."
            )

        path = Path(normalized_path)

        if not path.exists():
            raise SquadValidationError(
                "The selected players CSV file does not exist."
            )

        try:
            players = self._load_players(path)
        except Exception as exc:
            raise SquadValidationError(
                f"Could not load players CSV: {exc}"
            ) from exc

        return RosterResult(
            players=players,
            rows=self.map_players(players),
            source_path=str(path)
        )

    def map_players(self, players, selected_position=""):
        rankings = self._rankings_by_player(
            players,
            selected_position
        )

        rows = []

        for player in players:
            best_position, best_score = self._analyzer.best_position(
                player
            )
            ranking = rankings.get(
                player.name,
                (0.0, 0)
            )

            rows.append(
                PlayerRow(
                    name=player.name,
                    age=player.age,
                    form=player.form,
                    stamina=player.stamina,
                    experience=player.experience,
                    leadership=player.leadership,
                    tsi=player.tsi,
                    salary=player.salary,
                    goalkeeper=player.goalkeeper,
                    defending=player.defending,
                    playmaking=player.playmaking,
                    winger=player.winger,
                    passing=player.passing,
                    scoring=player.scoring,
                    set_pieces=player.set_pieces,
                    speciality=player.speciality,
                    selected_position_score=ranking[0],
                    selected_position_rank=ranking[1],
                    best_position=format_position(
                        normalize_position_value(best_position)
                    ),
                    best_position_score=float(best_score),
                )
            )

        return rows

    def filter_rows(
        self,
        rows,
        search_text="",
        minimum_form=0,
        minimum_stamina=0,
        speciality="",
        selected_position=""
    ):
        query = str(search_text).strip().lower()
        selected_speciality = str(speciality).strip()

        filtered = []

        for row in rows:
            if query and query not in row.name.lower():
                continue

            if row.form < int(minimum_form):
                continue

            if row.stamina < int(minimum_stamina):
                continue

            if selected_speciality and row.speciality != selected_speciality:
                continue

            filtered.append(row)

        if selected_position:
            filtered.sort(
                key=lambda row: row.selected_position_rank or 9999
            )

        return filtered

    def player_detail(self, players, player_name):
        player = next(
            (
                candidate for candidate in players
                if candidate.name == player_name
            ),
            None
        )

        if player is None:
            return None

        rows = self.map_players([player])
        rankings = []

        for label, position in SUPPORTED_POSITIONS.items():
            score = self._analyzer.rank_players(
                [player],
                position
            )[0].score
            rankings.append(
                (label, float(score), 1)
            )

        return PlayerDetail(
            player=rows[0],
            rankings=rankings
        )

    def export_rows_to_csv(self, rows, output_path):
        path = Path(output_path)

        if not path.parent.exists():
            path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

        field_names = [
            field.name
            for field in fields(PlayerRow)
        ]

        with open(
            path,
            "w",
            encoding="utf-8",
            newline=""
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=field_names
            )
            writer.writeheader()

            for row in rows:
                writer.writerow(
                    {
                        name: getattr(row, name)
                        for name in field_names
                    }
                )

        return str(path)

    def _load_players(self, path):
        importer = self._importer

        if importer is None:
            from importers.csv_importer import load_players

            importer = load_players

        return importer(str(path))

    def _rankings_by_player(self, players, selected_position):
        if selected_position not in SUPPORTED_POSITIONS:
            return {}

        ranking = self._analyzer.rank_players(
            players,
            SUPPORTED_POSITIONS[selected_position]
        )

        return {
            player_score.player.name: (
                float(player_score.score),
                index + 1
            )
            for index, player_score in enumerate(ranking)
        }
