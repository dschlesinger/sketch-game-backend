from dataclasses import dataclass, field
from typing import List

@dataclass
class City:
    is_capital: bool

@dataclass
class Army:
    faction_id: str
    numbers: int

@dataclass
class Port:
    pass

@dataclass
class Fort:
    pass

@dataclass
class Faction:
    faction_id: str
    name: str
    
    is_availale: bool
    is_defeated: bool
    turn_ended: bool

@dataclass
class Province:

    # Init all as undefined then mature

    province_id: str
    fractal_id: int
    name: str
    faction_id: str = None

    # If true only province_id, border, centriod, army, and neighbor
    # fields will be populated.
    is_ocean: bool = True

    border: List[List[float]] = None
    centriod: List[float] = None

    city: City | None = None
    army: Army | None = None
    fort: Fort | None = None
    port: Port | None = None

    # List of ids
    neighbors: List[str] = field(default_factory=list)

@dataclass
class GameState:
    
    game_id: str
    owner: str

    game_over: bool

    provinces: List[Province]
    continents: List[List[float]]
    factions: List[Faction]

def get_province(provinces: List[Province], province_id: str) -> Province | None:

    for p in provinces:

        if p.province_id == province_id:

            return p

    print(province_id, [p.province_id for p in provinces])
        
    return None

def get_faction(factions: List[Faction], faction_id: str) -> Faction | None:

    for f in factions:

        if f.faction_id == faction_id:

            return f
        
    return None

def get_province_by_fractal(province: List[Province], fractal_id: int) -> Province | None:

    for p in province:

        if p.fractal_id == fractal_id:

            return p
        
    return None