from dataclasses import dataclass


@dataclass
class Player:
    name: str
    age: int
    days: int

    speciality: str

    form: int
    stamina: int

    goalkeeper: int
    defending: int
    playmaking: int
    winger: int
    passing: int
    scoring: int
    set_pieces: int

    experience: int
    leadership: int

    tsi: int
    salary: int

    injury: float | None = None
    injury_raw: str = ""
