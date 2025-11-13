import json
import os
from typing import Dict, List
from dataclasses import asdict

from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import boto3
from dotenv import load_dotenv
import asyncio

from create_game.schema import GameState
from create_game.create_game import make_game
from llm.state_to_context import process as state_to_yaml, create_game_state_from_json
from llm.context_agent import generate_context
from llm.advisor_agent import get_advice, update_scratch_pad
from llm.end_turn_agent import process_turn_end, update_game_state, update_context

load_dotenv()

# -------------------- AWS S3 --------------------
aws_access_key = os.getenv('BOTO3_ACCESS_KEY') or os.getenv('BOTO3_ACSESS_KEY')
aws_secret_key = os.getenv('BOTO3_SECRET_KEY')
bucket_name = 'sketch-game-bucket'

s3 = boto3.resource(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-east-1'
)
bucket = s3.Bucket(bucket_name)

s3_lock = asyncio.Lock()  # lock for concurrent writes


# -------------------- S3 Helpers --------------------
async def read_s3_text(key: str) -> str:
    try:
        obj = bucket.Object(key).get()
        return obj['Body'].read().decode('utf-8')
    except s3.meta.client.exceptions.NoSuchKey:
        print(f"[WARN] Missing key: {key}")
        return ""


async def write_s3_text(key: str, body: str | bytes):
    async with s3_lock:
        if isinstance(body, str):
            body = body.encode('utf-8')
        bucket.put_object(Key=key, Body=body)


# -------------------- FastAPI Setup --------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected websocket clients: {game_id: set of WebSockets}
connected_clients: Dict[str, set] = {}


# -------------------- WebSocket Handler --------------------
@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    if game_id not in connected_clients:
        connected_clients[game_id] = set()
    connected_clients[game_id].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                route = message.get('route')
                payload = message.get('message')
                if route and payload:
                    await websocket_handler(game_id, route, payload)

                # Echo message back
                await websocket.send_text(json.dumps({"echo": message}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))

    except WebSocketDisconnect:
        connected_clients[game_id].remove(websocket)
        if not connected_clients[game_id]:
            del connected_clients[game_id]


async def websocket_handler(game_id: str, route: str, data: Dict):
    if route == "end_turn":
        faction_id = data["faction_id"]
        game_state_json = await read_s3_text(f'game-state/game-state-{game_id}.json')
        if not game_state_json:
            return

        game_state = json.loads(game_state_json)
        for f in game_state['factions']:
            if f['faction_id'] == faction_id:
                f['turn_ended'] = True

        if all(f['turn_ended'] for f in game_state['factions']):
            print(f"[INFO] All factions ended turn for game {game_id}")
            await end_turn(game_id)

        await write_s3_text(f'game-state/game-state-{game_id}.json', json.dumps(game_state))


# -------------------- End Turn Logic --------------------
async def end_turn(game_id: str):
    game_state_data = await read_s3_text(f'game-state/game-state-{game_id}.json')
    context_text = await read_s3_text(f'context/context-{game_id}.txt')

    scratch_pad_texts = []
    for f in json.loads(game_state_data)['factions']:
        scratch_pad_texts.append(await read_s3_text(f'advisor-scratch-pad/pad-{game_id}-{f["faction_id"]}.txt'))

    game_state_instance = create_game_state_from_json(game_state_data)
    game_state_yaml = state_to_yaml(game_state_data)

    updates = process_turn_end(context_text, game_state_yaml, scratch_pad_texts, game_state_instance)

    gs = update_game_state(s3, game_state_instance, updates, bucket_name)

    # Reset turn_ended flags
    for f in gs.factions:
        f.turn_ended = False

    new_gs_yaml = state_to_yaml(gs)
    await update_context(s3, bucket_name, game_id, context_text, new_gs_yaml, scratch_pad_texts)

    # Notify connected websocket clients
    if game_id in connected_clients:
        for ws in connected_clients[game_id]:
            try:
                await ws.send_text(json.dumps({"event": "turn_processed", "updates": [asdict(u) for u in updates]}))
            except Exception:
                pass


# -------------------- HTTP Endpoints --------------------
@app.get("/")
async def read_root():
    return {"message": "WebSocket server is running!"}


class GameRequest(BaseModel):
    owner: str
    number_people: int
    grain: int


@app.post("/create-game")
async def create_game(message: GameRequest) -> GameState:
    game_state = make_game(message.owner, message.number_people, message.grain)

    await write_s3_text(f'game-state/game-state-{game_state.game_id}.json', json.dumps(asdict(game_state)))
    game_state_yaml = state_to_yaml(game_state)
    context = generate_context(game_state_yaml)
    await write_s3_text(f'context/context-{game_state.game_id}.txt', context)

    for f in [f.faction_id for f in game_state.factions]:
        await write_s3_text(f'advisor-scratch-pad/pad-{game_state.game_id}-{f}.txt', '')

    print(f"[INFO] Created game {game_state.game_id}")
    return game_state


class AdvisorMessage(BaseModel):
    game_id: str
    faction_id: str
    message: str


@app.post("/advisor")
async def talk_w_advisor(message: AdvisorMessage):
    m = message

    game_state_data = await read_s3_text(f'game-state/game-state-{m.game_id}.json')
    context_text = await read_s3_text(f'context/context-{m.game_id}.txt')
    scratch_pad_text = await read_s3_text(f'advisor-scratch-pad/pad-{m.game_id}-{m.faction_id}.txt')

    game_state_yaml = state_to_yaml(game_state_data)
    advice = get_advice(m.faction_id, context_text, game_state_yaml, scratch_pad_text, m.message)

    new_scratch_pad = update_scratch_pad(m.faction_id, context_text, game_state_yaml, scratch_pad_text, m.message)
    await write_s3_text(f'advisor-scratch-pad/pad-{m.game_id}-{m.faction_id}.txt', new_scratch_pad)

    return {"advice": advice}


# -------------------- Main --------------------
def main():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
