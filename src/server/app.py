import random
import json
from typing import Generator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from server.schema import GameCreate, Game, GAME_ID_CHARS, Player, AdvisorChat, GameCreateStep
from server.settings import settings
from server.manager import manager
from server.websocket_handler import route_websocket
from game.schema import GameState, get_faction
from game.create_game import make_game
from llm.advisor import advisor, init_advising_notes
from llm.game_context import init_game_context
from files.schema import GameNotFoundException

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

# For checking if the server is active
@app.get('/')
def is_active() -> None:

    return {
        'message': 'It\'s possible. I have friends everywhere.'
    }

# I/O bound opperation use async def
@app.get('/game-info/{game_id}')
async def game_info(game_id: str) -> GameState:

    print(game_id)

    try:
        game_state = storage.get_game_state(game_id)
    except GameNotFoundException:

        raise HTTPException(
            status_code=500,
            detail='Game ID not found'
        )

    return game_state

# def instead of async def as this is not an I/O bound opperation
@app.post('/create-game')
def create_game(game: GameCreate) -> StreamingResponse:

    def create_game_pipeline(game: GameCreate) -> Generator:
        try:
            game_id = ''.join([random.choice(GAME_ID_CHARS) for _ in range(6)])

            yield f"data: {GameCreateStep(step='map', game_id=game_id).model_dump_json()}\n\n"

            game_state = make_game(
                game_id,
                game.name,
                game.owner,
                game.nplayers,
                game.grain
            )

            storage.set_game_state(game_id, game_state)

            yield f"data: {GameCreateStep(step='lore', game_id=game_id).model_dump_json()}\n\n"

            init_game_context(game_id, storage)
            init_advising_notes(game_id, game_state.factions, storage)

            yield f"data: {GameCreateStep(step='final', game_id=game_id).model_dump_json()}\n\n"
            
        except Exception as e:
            error_data = json.dumps({"error": str(e), "step": "error"})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        create_game_pipeline(game),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post('/join-game')
async def join_game(player: Player) -> None:

    try:
        game_state = storage.get_game_state(player.game_id)
    except GameNotFoundException:
        return HTTPException(
            status_code=500,
            detail='Game ID not found'
        )

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

    stream_chat = advisor(chat.game_id, chat.faction_id, chat.messages, storage)

    return StreamingResponse(stream_chat)

@app.websocket("/ws/attach-game")
async def websocket_endpoint(websocket: WebSocket, game_id: str, faction_id: str):

    print(game_id, faction_id)
    if game_id is None or faction_id is None:
        # Not a valid attachment request
        return

    await manager.connect(websocket, game_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                route = message.get('route')
                payload = message.get('message')
                if route is not None and payload is not None:
                    print(route, payload)
                    await route_websocket(game_id, faction_id, route, payload, manager, storage)
                else:
                    print('invalid ws package', route, payload)
                # Send Game State
                # await websocket.send_text(json.dumps({"echo": message}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)