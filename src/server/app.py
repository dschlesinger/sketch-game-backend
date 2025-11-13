import random

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from server.schema import GameCreate, Game, GAME_ID_CHARS, Player, get_faction
from server.settings import settings
from game.schema import GameState
from game.create_game import make_game

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage Manager
if settings.devolopment:
    from files.local import LocalStorage

    storage = LocalStorage()
else:
    # Prod
    raise NotImplementedError('Production storage not implemented')

# I/O bound opperation use async def
@app.get('/game-info/{game_id}')
async def game_info(game_id: str) -> GameState:

    print(game_id)

    if not game_id in storage.all_game_ids:

        raise HTTPException(
            status_code=500,
            detail='Game ID not found'
        )

    return storage.get_game_state(game_id)

# def instead of async def as this is not an I/O bound opperation
@app.post('/create-game')
def create_game(game: GameCreate) -> Game:

    game_id = ''.join([random.choice(GAME_ID_CHARS) for _ in range(6)])

    game_state = make_game(
        game_id,
        game.owner,
        game.nplayers,
        game.grain
    )

    storage.set_game_state(game_id, game_state)

    return Game(
        game_id=game_id
    )

@app.post('/join-game')
async def join_game(player: Player) -> None:

    game_state = storage.get_game_state(player.game_id)

    f = get_faction(player.faction_id, game_state)

    if not f.available:

        return HTTPException('Faction is taken')

    else:

        print(
            f"{f.name} has joined {player.game_id}"
        )

    # Set player to taken
    f.available = False