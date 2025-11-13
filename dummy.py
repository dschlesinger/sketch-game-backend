import random
import string
import json
from typing import List, Dict, Set

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

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

# class ConnectedPlayer(BaseModel):
#     game_id: str
#     faction_id: str

#     def __hash__(self):
#         return f'{self.game_id}|{self.faction_id}'

# connected_players: Dict[ConnectedPlayer, WebSocket] = {}

# Do by games
class ConnectionManager:
    def __init__(self):
        self.active_games: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()

        if game_id not in self.active_games:
            self.active_games[game_id] = set()

        self.active_games[game_id].add(websocket)

        # Send game state
        # self.send_game_state({}, websocket)

        print("Client connected:", websocket.client)

    def disconnect(self, websocket: WebSocket, game_id: str):
        self.active_games[game_id].remove(websocket)
        if not self.active_games[game_id]:
            del self.active_games[game_id]
        print("Client disconnected:", websocket.client)

    async def send_game_state(self, game_state, websocket: WebSocket):
        await websocket.send_text(game_state.model_dump())

    async def broadcast_updates(self, updates: List, game_id: str):
        for connection in self.active_connections[game_id]:
            await connection.send_text(updates)

manager = ConnectionManager()

# -------------------- WebSocket Handler --------------------
@app.websocket("/ws/attach-game")
async def websocket_endpoint(websocket: WebSocket, game_id: str, faction_id: str):
    await manager.connect(websocket, game_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                route = message.get('route')
                payload = message.get('message')
                if route and payload:
                    print(route, payload)

                # Send Game State
                await websocket.send_text(json.dumps({"echo": message}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)

if __name__ == '__main__':

    uvicorn.run(app)