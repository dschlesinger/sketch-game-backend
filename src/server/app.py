import random
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from server.schema import GameCreate, Game, GAME_ID_CHARS, Player, AdvisorChat
from server.settings import settings
from server.manager import manager
from server.websocket_handler import route_websocket
from game.schema import GameState, get_faction
from game.create_game import make_game
from llm.advisor import advisor

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
        game.name,
        game.owner,
        game.nplayers,
        game.grain
    )

    storage.set_game_state(game_id, game_state)

    print('Setting storage')

    return Game(
        game_id=game_id
    )

@app.post('/join-game')
async def join_game(player: Player) -> None:

    game_state = storage.get_game_state(player.game_id)

    f = get_faction(game_state.factions, player.faction_id)

    if not f.available:

        return HTTPException(
            status_code=500,
            detail='Faction is taken'
        )

    else:

        print(
            f"{f.name} has joined {player.game_id}"
        )

    # Set player to taken
    f.available = False

    storage.set_game_state(player.game_id, game_state)

@app.post("/advisor")
def advisor_chat(chat: AdvisorChat) -> StreamingResponse:

    stream_chat = advisor(chat.faction_id, chat.messages)

    return StreamingResponse(stream_chat)

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
                    await route_websocket(game_id, faction_id, route, payload, storage)

                # Send Game State
                await websocket.send_text(json.dumps({"echo": message}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)