import json, requests
from typing import Dict

from create_game.schema import GameState
from create_game.create_game import make_game

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

N8N_ROUTE = 'http://localhost:5678/'

def websocket_handler(route: str, data: Dict) -> Dict:
    """Handle events from websocket
    """

    match route:

        case 'ping_n8n':

            r = requests.get(N8N_ROUTE)

            print(f"Pinged n8n with response {r.status_code}")

        case _:

            print(f'No handler for {route}')

    return {}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # You can use ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket handling ---
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

# --- Optional HTTP route ---
@app.get("/")
def read_root():
    return {"message": "WebSocket server is running!"}

class GameRequest(BaseModel):
    owner: str
    number_people: int

@app.post("/create-game")
async def create_game(message: GameRequest) -> GameState:

    owner = message.owner
    number_people = message.number_people

    game_state = make_game(owner, number_people)

    return game_state

def main() -> None:

    uvicorn.run(app, port=8000)

if __name__ == '__main__':

    main()