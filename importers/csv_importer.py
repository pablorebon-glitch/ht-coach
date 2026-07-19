import pandas as pd

from models.player import Player


INJURY_COLUMN = "Lesiones"


def parse_injury_value(value):

    if pd.isna(value):
        return None, ""

    raw = str(value).strip()

    if not raw:
        return None, raw

    try:
        numeric = float(raw.replace(",", "."))
    except (TypeError, ValueError):
        return None, raw

    return numeric, raw


def load_players(path: str):

    df = pd.read_csv(path)

    players = []

    for _, row in df.iterrows():

        injury_value, injury_raw = parse_injury_value(
            row[INJURY_COLUMN]
            if INJURY_COLUMN in row
            else None
        )

        player = Player(
            name=row["Nombre"],
            age=int(row["Edad"]),
            days=int(row["Días"]),
            speciality="" if pd.isna(row["Especialidad"]) else row["Especialidad"],
            form=int(row["Forma"]),
            stamina=int(row["Condición"]),
            goalkeeper=int(row["Portería"]),
            defending=int(row["Defensa"]),
            playmaking=int(row["Jugadas"]),
            winger=int(row["Lateral"]),
            passing=int(row["Pases"]),
            scoring=int(row["Anotación"]),
            set_pieces=int(row["Balón parado"]),
            experience=int(row["Experiencia"]),
            leadership=int(row["Liderazgo"]),
            tsi=int(row["TSI"]),
            salary=int(row["Salario"]),
            injury=injury_value,
            injury_raw=injury_raw
        )

        players.append(player)

    return players
