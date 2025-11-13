import random
import string
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

app = FastAPI()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# For testing

class Faction(BaseModel):
    faction_id: str
    name: str
    is_taken: bool

class GameInfo(BaseModel):
    game_id: str
    name: str
    factions: List[Faction]

demo_factions = [
    Faction(faction_id='abc123', name='The Iron Legion', is_taken=False),
    Faction(faction_id='def456', name='Emerald Order', is_taken=True),
    Faction(faction_id='ghi789', name='Sapphire Syndicate', is_taken=False),
    Faction(faction_id='jkl012', name='Crimson Dominion', is_taken=True),
    Faction(faction_id='mno345', name='Obsidian Circle', is_taken=False),
]

games = {
    'test': GameInfo(
        game_id='test',
        name='random',
        factions=demo_factions
    )
}

def get_faction(faction_id: str) -> Faction | None:

    for f in demo_factions:

        if f.faction_id == faction_id:

            return f

@app.get('/game-info/{game_id}')
async def game_info(game_id: str) -> GameInfo:

    print(game_id)

    if not game_id in games:

        raise HTTPException(
            status_code=500,
            detail='Game ID not found'
        )

    demo = games[game_id]

    return demo.model_dump()

class GameCreate(BaseModel):

    owner: str
    name: str

    nplayers: int
    grain: int

    # Validate that nplayers and grain are within constraints
    @field_validator('nplayers')
    @classmethod
    def limit_players(cls, n: int) -> int:
        if not 20 >= n > 1:
            raise ValueError('nplayers must be 20 >= n > 1')
        return n
    
    @field_validator('grain')
    @classmethod
    def limit_players(cls, grain: int) -> int:
        if not 500 >= grain >= 10:
            raise ValueError('grain must be 500 >= grain >= 10')
        return grain

class Game(BaseModel):
    game_id: str

GAME_ID_CHARS = [*string.ascii_uppercase] + [str(i) for i in range(0, 10)]

# def instead of async def as this is not an I/O bound opperation
@app.post('/create-game')
def create_game(game: GameCreate) -> Game:

    game_id = ''.join([random.choice(GAME_ID_CHARS) for _ in range(6)])

    games[game_id] = games['test']
    games[game_id].game_id = game_id

    return Game(
        game_id=game_id
    )

class Player(BaseModel):
    game_id: str
    faction_id: str

@app.post('/join-game')
async def join_game(player: Player) -> bool:

    f = get_faction(player.faction_id)

    if f.is_taken:

        print('Cannot join')

        return False

    else:

        print(
            f"{f.name} has joined {player.game_id}"
        )

    # Set player to taken
    f.is_taken = True

    return True

if __name__ == '__main__':

    uvicorn.run(app)