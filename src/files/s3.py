from typing import Dict
import json

import boto3

from server.settings import settings
from files.exceptions import GameNotFoundException
from game.schema import GameState


class S3Storage:
    bucket_name: str = 'sketch-game-bucket'
    context_route: str = 'context'
    game_state_route: str = 'game-state'
    advisor_notes_route: str = 'advisor-scratch-pad'
    faction_interaction_route: str = 'faction-interactions'

    def __init__(self) -> None:
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.BOTO3_ACCESS_KEY,
            aws_secret_access_key=settings.BOTO3_SECRET_KEY,
        )

    # ------------------------
    # Low-level helpers
    # ------------------------

    def write_text(self, key: str, text: str) -> None:
        if isinstance(text, str):
            text = text.encode("utf-8")

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=text,
        )

    def read_text(self, key: str) -> str:
        try:
            obj = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
        except self.client.exceptions.NoSuchKey as NSK:
            raise GameNotFoundException from NSK

        return obj['Body'].read().decode("utf-8")

    def write_json(self, key: str, data: Dict) -> None:
        text = json.dumps(data)
        self.write_text(key, text)

    def read_json(self, key: str) -> Dict:
        text = self.read_text(key)
        return json.loads(text)

    # ---- Context ----
    def get_context(self, game_id: str) -> str:
        key = f"{self.context_route}/{game_id}.txt"
        return self.read_text(key)

    def set_context(self, game_id: str, context: str) -> None:
        key = f"{self.context_route}/{game_id}.txt"
        self.write_text(key, context)

    # ---- Game state ----
    def get_game_state(self, game_id: str) -> GameState:
        key = f"{self.game_state_route}/{game_id}.json"
        data = self.read_json(key)
        return GameState(**data)

    def set_game_state(self, game_id: str, game_state: GameState) -> None:
        key = f"{self.game_state_route}/{game_id}.json"
        self.write_json(key, game_state.model_dump())

    # ---- Advisor notes ----
    def get_advisor_notes(self, game_id: str, faction_id: str) -> str:
        key = f"{self.advisor_notes_route}/{game_id}.{faction_id}.txt"
        return self.read_text(key)

    def set_advisor_notes(self, game_id: str, faction_id: str, notes: str) -> None:
        key = f"{self.advisor_notes_route}/{game_id}.{faction_id}.txt"
        self.write_text(key, notes)

    def get_faction_interactions(self, game_id: str, faction_1_id: str, faction_2_id: str) -> str:

        first_faction, second_faction = max(faction_1_id, faction_2_id), min(faction_1_id, faction_2_id)

        key = f"{self.faction_interaction_route}/{game_id}-{first_faction}-{second_faction}.txt"
        return self.read_text(key)

    def set_faction_interactions(self, game_id: str, faction_1_id: str, faction_2_id: str, interaction: str) -> None:

        first_faction, second_faction = max(faction_1_id, faction_2_id), min(faction_1_id, faction_2_id)

        key = f"{self.faction_interaction_route}/{game_id}-{first_faction}-{second_faction}.txt"

        self.write_text(key, interaction)
        
    # Need to add messaging

if __name__ == '__main__':

    storage = S3Storage()

    game_id = "test-1"
    faction_a = "A"
    faction_b = "B"

    print("---- Test 1: Write & Read Context ----")
    storage.set_context(game_id, "This is a test context.")
    context = storage.get_context(game_id)
    print("Context:", context)

    print("\n---- Test 2: Write & Read Game State ----")
    test_state = GameState(
        game_id=game_id,
        name='test-1',
        owner='no one',
        factions=[],
        provinces=[],
    )
    storage.set_game_state(game_id, test_state)
    loaded_state = storage.get_game_state(game_id)
    print("Game state:", loaded_state.model_dump())

    print("\n---- Test 3: Write & Read Advisor Notes ----")
    storage.set_advisor_notes(game_id, faction_a, "Notes for faction A.")
    notes = storage.get_advisor_notes(game_id, faction_a)
    print("Advisor notes:", notes)

    print("\n---- Test 4: Faction Interaction Write & Read ----")
    storage.set_faction_interactions(game_id, faction_a, faction_b, "Alliance formed.")
    interaction = storage.get_faction_interactions(game_id, faction_a, faction_b)
    print("Interaction:", interaction)

    print("\n---- Test 5: Missing Key Error ----")
    try:
        storage.get_context("does-not-exist")
    except GameNotFoundException:
        print("Correctly raised GameNotFoundException for missing context.")
