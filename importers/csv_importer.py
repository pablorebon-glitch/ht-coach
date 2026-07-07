import pandas as pd

from models.player import Player


def load_players(path: str):

    df = pd.read_csv(path)

    players = []

    for _, row in df.iterrows():

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
            salary=int(row["Salario"])
        )

        players.append(player)

    return players