import json
import os
from typing import Dict, List

from game.schema import GameState
from files.exceptions import GameNotFoundException
from files.schema import get_faction_order, Message

class LocalStorage:
    base_route: str = "dev"  # base folder for all "routes"

    context_route: str = "game_context"
    game_state_route: str = "game_state"
    advisor_notes_route: str = "advisor_notes"
    faction_interaction_route: str = "faction_interactions"
    messages_route: str = 'messages'

    def __init__(self) -> None:
        # ensure base folder exists
        os.makedirs(self.base_route, exist_ok=True)

    # ------------------------
    # Low-level helpers
    # ------------------------

    def _full_path(self, key: str) -> str:
        """Prefix key with base_route base folder."""
        return os.path.join(self.base_route, key)

    def write_text(self, key: str, text: str) -> None:
        path = self._full_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def read_text(self, key: str) -> str:
        path = self._full_path(key)

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError as FNFE:
            raise GameNotFoundException from FNFE

    def write_json(self, key: str, data: Dict) -> None:
        text = json.dumps(data)
        self.write_text(key, text)

    def read_json(self, key: str) -> Dict:
        text = self.read_text(key)
        return json.loads(text)

    # ------------------------
    # Context
    # ------------------------

    def get_context(self, game_id: str) -> str:
        key = f"{self.context_route}/{game_id}.txt"
        return self.read_text(key)

    def set_context(self, game_id: str, context: str) -> None:
        key = f"{self.context_route}/{game_id}.txt"
        self.write_text(key, context)

    # ------------------------
    # Game State
    # ------------------------

    def get_game_state(self, game_id: str) -> GameState:
        key = f"{self.game_state_route}/{game_id}.json"
        data = self.read_json(key)
        return GameState(**data)

    def set_game_state(self, game_id: str, game_state: GameState) -> None:
        key = f"{self.game_state_route}/{game_id}.json"
        self.write_json(key, game_state.model_dump())

    # ------------------------
    # Advisor Notes
    # ------------------------

    def get_advisor_notes(self, game_id: str, faction_id: str) -> str:
        key = f"{self.advisor_notes_route}/{game_id}.{faction_id}.txt"
        return self.read_text(key)

    def set_advisor_notes(self, game_id: str, faction_id: str, notes: str) -> None:
        key = f"{self.advisor_notes_route}/{game_id}.{faction_id}.txt"
        self.write_text(key, notes)

    # ------------------------
    # Faction Interactions
    # ------------------------

    def get_faction_interactions(self, game_id: str, faction_1_id: str, faction_2_id: str) -> str:
        first_faction, second_faction = get_faction_order(faction_1_id, faction_2_id)
        key = f"{self.faction_interaction_route}/{game_id}.{first_faction}.{second_faction}.txt"
        return self.read_text(key)

    def set_faction_interactions(self, game_id: str, faction_1_id: str, faction_2_id: str, interaction: str) -> None:
        first_faction, second_faction = get_faction_order(faction_1_id, faction_2_id)
        key = f"{self.faction_interaction_route}/{game_id}.{first_faction}.{second_faction}.txt"
        self.write_text(key, interaction)

    # ------------------------
    # Messaging
    # ------------------------
    def get_messages(self, game_id: str, faction_1_id: str, faction_2_id: str) -> List[Message]:
        first_faction, second_faction = get_faction_order(faction_1_id, faction_2_id)
        key = f"{self.messages_route}/{game_id}.{first_faction}.{second_faction}.txt"
        data = self.read_json(key)
        return [Message(m) for m in data.get('messages', [])]
    
    def set_messages(self, game_id: str, faction_1_id: str, faction_2_id: str, messages: List[Message]) -> None:
        first_faction, second_faction = get_faction_order(faction_1_id, faction_2_id)
        key = f"{self.messages_route}/{game_id}.{first_faction}.{second_faction}.txt"
        data = {
            'messages': [m.model_dump() for m in messages]
        }
        self.write_json(key, data)

    def add_message(self, game_id: str, faction_1_id: str, faction_2_id: str, message: Message) -> None:
        first_faction, second_faction = get_faction_order(faction_1_id, faction_2_id)
        key = f"{self.messages_route}/{game_id}.{first_faction}.{second_faction}.txt"
        messages = self.read_json(key).get('messages', [])
        if not isinstance(messages, List):
            raise TypeError(f'Messages from file must be list found {messages}')
        messages.append(message)
        data = {
            'messages': [m.model_dump() for m in messages]
        }
        self.write_json(key, data)

if __name__ == "__main__":

    storage = LocalStorage()

    game_id = "local-test-1"
    faction_a = "A"
    faction_b = "B"

    print("---- Test 1: Write & Read Context ----")
    storage.set_context(game_id, "Local context test")
    print("Context:", storage.get_context(game_id))

    print("\n---- Test 2: Write & Read Game State ----")
    test_state = GameState(
        game_id=game_id,
        name='local-test-1',
        owner='nobody',
        factions=[],
        provinces=[],
    )
    storage.set_game_state(game_id, test_state)
    loaded_state = storage.get_game_state(game_id)
    print("Game state:", loaded_state.model_dump())

    print("\n---- Test 3: Write & Read Advisor Notes ----")
    storage.set_advisor_notes(game_id, faction_a, "Local notes for A")
    print("Advisor notes:", storage.get_advisor_notes(game_id, faction_a))

    print("\n---- Test 4: Faction Interaction Write & Read ----")
    storage.set_faction_interactions(game_id, faction_a, faction_b, "Local alliance formed.")
    print("Interaction:", storage.get_faction_interactions(game_id, faction_a, faction_b))

    print("\n---- Test 5: Missing Key Error ----")
    try:
        storage.get_context("does-not-exist")
    except GameNotFoundException:
        print("Correctly raised GameNotFoundException for missing context.")

    print("\n---- Test 6: Make Messages ----")
    storage.set_messages(game_id, faction_a, faction_b, [])

    print("\n---- Test 7: Append a Message ----")
    m = Message(
        role='me',
        message='hello world'
    )
    storage.add_message(game_id, faction_a, faction_b, m)

    print("\n---- Test 8: Load Messages ----")
    storage.get_messages(game_id, faction_a, faction_b)
