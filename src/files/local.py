import json
import os
from typing import Dict, Set

from pydantic import BaseModel

from game.schema import GameState

class LocalStorage(BaseModel):

    context_route: str = 'dev/game_context'
    game_state_route: str = 'dev/game_state'
    advisor_notes_route: str = 'dev/advisor_notes'

    @property
    @staticmethod
    def all_game_ids(self) -> Set[str]:

        all_game_ids = set()

        # Check game state routes
        for game_state in os.listdir(self.game_state_route):

            game_id = game_state.removesuffix('.json')

            all_game_ids.add(game_id)

        return all_game_ids

    @staticmethod
    def load_txt(path: str) -> str:

        with open(path, 'r') as f:

            text = f.read()
        
        return text
    
    @staticmethod
    def write_txt(path: str, text: str) -> None:

        with open(path, 'w') as f:

            f.write(text)
    
    @staticmethod
    def load_json(path: str) -> Dict:

        with open(path, 'r') as f:

            data = json.load(f)
        
        return data

    @staticmethod
    def write_json(path: str, data: Dict) -> None:

        with open(path, 'w') as f:

            json.dump(data, f)

    def get_context(self, game_id: str) -> str:

        path = f'{self.context_route}/{game_id}.txt'

        context = self.load_file(path)

        return context
    
    def set_context(self, game_id: str, context: str) -> None:

        path = f'{self.context_route}/{game_id}.txt'

        self.write_txt(path, context)

    def get_game_state(self, game_id: str) -> GameState:

        path = f'{self.game_state_route}/{game_id}.json'

        game_state = self.load_json(path)

        return GameState(**game_state)
    
    def set_game_state(self, game_id: str, game_state: GameState) -> None:

        path = f'{self.game_state_route}/{game_id}.json'
        
        self.write_json(path, game_state.model_dump())

    def get_advisor_notes(self, game_id: str, faction_id: str) -> str:

        path = f'{self.advisor_notes_route}/{game_id}.{faction_id}.txt'

        notes = self.load_txt(path)

        return notes
    
    def set_advisor_notes(self, game_id: str, faction_id: str, notes: str) -> None:

        path = f'{self.advisor_notes_route}/{game_id}.{faction_id}.txt'
        
        self.write_txt(path, notes)