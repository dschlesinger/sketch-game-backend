import string
from typing import List

from pydantic import BaseModel, field_validator

from llm.advisor import AdvisorMessage

class GameCreate(BaseModel):

    owner: str
    name: str

    nplayers: int
    grain: int

    # Validate that nplayers and grain are within constraints
    # Make sure these are up to date with the front end
    @field_validator('nplayers')
    @classmethod
    def limit_players(cls, n: int) -> int:
        if not 20 >= n > 1:
            raise ValueError('nplayers must be 20 >= n > 1')
        return n
    
    @field_validator('grain')
    @classmethod
    def limit_grain(cls, grain: int) -> int:
        if not 500 >= grain >= 10:
            raise ValueError('grain must be 500 >= grain >= 10')
        return grain

GAME_ID_CHARS = [*string.ascii_uppercase] + [str(i) for i in range(0, 10)]

# Return GameID to front end
class Game(BaseModel):
    game_id: str

class Player(BaseModel):
    game_id: str
    faction_id: str

class AdvisorChat(BaseModel):
    game_id: str
    faction_id: str

    messages: List[AdvisorMessage]