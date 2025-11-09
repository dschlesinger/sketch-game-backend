import json, requests, os
from typing import Dict
from dataclasses import asdict
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import boto3
from dotenv import load_dotenv

from create_game.schema import GameState
from create_game.create_game import make_game
from llm.state_to_context import process as state_to_yaml, create_game_state_from_json
from llm.context_agent import generate_context
from llm.advisor_agent import get_advice, update_scratch_pad
from llm.end_turn_agent import process_turn_end, update_game_state, update_context

load_dotenv()

# --- AWS S3 setup ---
aws_access_key = os.getenv('BOTO3_ACCESS_KEY') or os.getenv('BOTO3_ACSESS_KEY')
aws_secret_key = os.getenv('BOTO3_SECRET_KEY')

s3 = boto3.resource(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name='us-east-1'
)

bucket_name = 'sketch-game-bucket'
bucket = s3.Bucket(bucket_name)


# --- Helper functions ---
def read_s3_text(key: str) -> str:
    """Fetch a text file from S3 and decode it safely."""
    try:
        obj = bucket.Object(key).get()
        return obj['Body'].read().decode('utf-8')
    except s3.meta.client.exceptions.NoSuchKey:
        print(f"[WARN] Missing key: {key}")
        return ""


def write_s3_text(key: str, body: str | bytes):
    """Upload text or bytes to S3."""
    if isinstance(body, str):
        body = body.encode('utf-8')
    bucket.put_object(Key=key, Body=body)


# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def endturn(game_id: str):
    
    game_state_data = read_s3_text(f'game-state/game-state-{game_id}.json')
    context_text = read_s3_text(f'context/context-{game_id}.txt')
    scratch_pad_texts = []
    
    for f in json.loads(game_state_data)['factions']:
        scratch_pad_texts.append(read_s3_text(f'advisor-scratch-pad/pad-{game_id}-{f["faction_id"]}.txt'))

    if not game_state_data:
        return {"error": f"Game state not found for {game_id}"}

    game_state_yaml = state_to_yaml(game_state_data)
    updates = process_turn_end(context_text, game_state_yaml, scratch_pad_texts, create_game_state_from_json(game_state_data))

    gs = update_game_state(s3, create_game_state_from_json(game_state_data), updates, 'sketch-game-bucket')

    # Reset everyone to not end turn
    for f in gs.factions:

        f.turn_ended = False

    new_gs_yaml = state_to_yaml(gs)

    update_context(s3, bucket_name, game_id, context_text, new_gs_yaml, scratch_pad_texts)

    return updates


def websocket_handler(route: str, data: Dict) -> Dict:
    match route:
        case 'end_turn':
            game_id = data['game_id']
            faction_id = data['faction_id']

            # Read and update game state
            game_state_json = read_s3_text(f'game-state/game-state-{game_id}.json')
            if not game_state_json:
                print(f"[ERROR] Missing game state for {game_id}")
                return {}

            game_state = json.loads(game_state_json)
            for f in game_state['factions']:
                if f['faction_id'] == faction_id:
                    f['turn_ended'] = True

            if all(f['turn_ended'] for f in game_state['factions']):
                print('Everyone ended turn')

                endturn(data['game_id'])

            # Write updated state back
            write_s3_text(f'game-state/game-state-{game_id}.json', json.dumps(game_state))
        case _:
            print(f'No handler for {route}')
    return {}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received: {data}")
            try:
                data = json.loads(data)
                await websocket.send_text(f"Echo: {data}")
                websocket_handler(data['route'], data['message'])
            except json.JSONDecodeError:
                print(f'Entity {data} is not processable')
    except WebSocketDisconnect:
        print("Client disconnected")


@app.get("/")
def read_root():
    return {"message": "WebSocket server is running!"}


class GameRequest(BaseModel):
    owner: str
    number_people: int
    grain: int


@app.post("/create-game")
async def create_game(message: GameRequest) -> GameState:
    game_state = make_game(message.owner, message.number_people, message.grain)

    # Save game state JSON
    write_s3_text(f'game-state/game-state-{game_state.game_id}.json', json.dumps(asdict(game_state)))

    # Generate and save context
    game_state_yaml = state_to_yaml(game_state)
    context = generate_context(game_state_yaml)
    write_s3_text(f'context/context-{game_state.game_id}.txt', context)

    # Create empty advisor scratch pads
    for f in [f.faction_id for f in game_state.factions]:
        write_s3_text(f'advisor-scratch-pad/pad-{game_state.game_id}-{f}.txt', '')

    print(game_state.game_id)
    return game_state


class AdvisorMessage(BaseModel):
    game_id: str
    faction_id: str
    message: str


@app.post("/advisor")
async def talk_w_advisor(message: AdvisorMessage) -> Dict:
    m = message

    game_state_data = read_s3_text(f'game-state/game-state-{m.game_id}.json')
    context_text = read_s3_text(f'context/context-{m.game_id}.txt')
    scratch_pad_text = read_s3_text(f'advisor-scratch-pad/pad-{m.game_id}-{m.faction_id}.txt')

    if not game_state_data:
        return {"error": f"Game state not found for {m.game_id}"}

    game_state_yaml = state_to_yaml(game_state_data)
    advice = get_advice(m.faction_id, context_text, game_state_yaml, scratch_pad_text, m.message)

    new_scratch_pad = update_scratch_pad(m.faction_id, context_text, game_state_yaml, scratch_pad_text, m.message)

    write_s3_text(f'advisor-scratch-pad/pad-{m.game_id}-{m.faction_id}.txt', new_scratch_pad)

    print(advice)
    return {'advice': advice}


def main() -> None:
    uvicorn.run(app, port=8000)


if __name__ == '__main__':
    main()
