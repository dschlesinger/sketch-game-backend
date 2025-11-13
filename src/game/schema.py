from typing import List

from pydantic import BaseModel, Field


class City(BaseModel):
    is_capital: bool

class Army(BaseModel):
    army_id: str
    faction_id: str

    numbers: int

class Port(BaseModel):
    pass

class Fort(BaseModel):
    pass

class Faction(BaseModel):
    faction_id: str
    name: str
    
    available: bool
    defeated: bool
    turn_ended: bool

class Province(BaseModel):
    province_id: str
    fractal_id: str
    name: str | None = None

    # Who controls province
    faction_id: str | None = None
    
    # This is for ocean tiles
    # If True only select fields will be populated
    # province_id, fractal_id, border, centriod, \
    # armies, & neighbors
    is_ocean: bool = True

    border: List[List[float]] = None
    centriod: List[float] = None

    city: City | None = None
    army: List[Army] = []
    fort: Fort | None = None
    port: Port | None = None

    # List of ids
    neighbors: List[str] = Field(default_factory=list)

class GameState(BaseModel):
    game_id: str
    name: str
    owner: str

    factions: List[Faction]
    provinces: List[Province]

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