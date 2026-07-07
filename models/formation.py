from dataclasses import dataclass

from models.position import Position


@dataclass
class Formation:

    name: str

    positions: dict[Position, int]
    
    experience: str = "Excellent"