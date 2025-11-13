from typing import Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_games: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str):
        await websocket.accept()

        if game_id not in self.active_games:
            self.active_games[game_id] = set()

        self.active_games[game_id].add(websocket)

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