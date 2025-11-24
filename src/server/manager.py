from typing import Dict, List, Set
import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from server.schema import GameUpdateList
from files.schema import Message

class ConnectionManager:
    def __init__(self):
        self.active_games: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str, faction_id: str):
        await websocket.accept()

        if game_id not in self.active_games:
            self.active_games[game_id]= {}

        self.active_games[game_id][faction_id] = websocket

        print("Client connected:", websocket.client)

    def disconnect(self, websocket: WebSocket, game_id: str, faction_id: str):
        del self.active_games[game_id][faction_id]
        if not self.active_games[game_id]:
            del self.active_games[game_id]
        print("Client disconnected:", websocket.client)

    async def send_game_state(self, game_state, websocket: WebSocket):
        await websocket.send_text(game_state.model_dump())
        
    def send_message(self, game_id: str, to_fid: str, message: Message):
        websocket = self.active_games[game_id].get(to_fid, None)
        
        if websocket is None:
            print(f'Could not find active {to_fid}')
            return
        
        async def smsg():
            await websocket.send_text(message.model_dump_json())
        
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        new_loop.run_until_complete(smsg())

    async def broadcast_updates(self, game_id: str, updates: GameUpdateList):
        for connection in self.active_games[game_id].values():
            print('Sending update')
            await connection.send_text(updates.model_dump_json())

manager = ConnectionManager()