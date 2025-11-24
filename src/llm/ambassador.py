from typing import List, Literal, Generator

from pydantic import BaseModel

from game.schema import get_faction
from files.general import Storage
from files.schema import Message
from llm.client import client
from llm.llm_game_state import process
from llm.helper_func import load_prompt, load_gamerules

def init_faction_relationships(game_id: str, faction_ids: List[str], storage: Storage) -> None:

    for i, f1 in enumerate(faction_ids):
        for f2 in faction_ids[i + 1 : ]:
            storage.set_faction_interactions(game_id, f1, f2, '')

# Streaming
def ambassador(game_id: str, faction_1_id: str, faction_2_id: str, chats: List[Message], storage: Storage):
    advisor_prompt = load_prompt('ambassador')
    game_rules = load_gamerules()
    game_state = storage.get_game_state(game_id)
    game_state_yaml = process(game_state)
    context = storage.get_context(game_id)
    ambassador_notes = storage.get_faction_interactions(game_id, faction_1_id, faction_2_id)

    f1 = get_faction(game_state.factions, faction_1_id)
    f2 = get_faction(game_state.factions, faction_2_id)

    game_rules_section = f"### Game Rules\n{game_rules}\n"
    faction_1_section = f"### Your Faction\nYou are a part of faction {f1.name} (faction name) {f1.faction_id} (faction_id)\n"
    faction_2_section = f"### You are Talking with Faction\n{f2.name} (faction name) {f2.faction_id} (faction_id)\n"
    game_state_section = f"### Game State\n{game_state_yaml}\n"
    context_section = f"### Game Context (Lore)\n{context}\n"
    ambassador_notes_section = f"### Notes from previous turns\n{ambassador_notes}\n"

    system_prompt = '\n'.join([advisor_prompt, game_rules_section, faction_1_section, faction_2_section, \
                               game_state_section, context_section, ambassador_notes_section
                            ])
    
    messages = [
            {"role": "system", "content": system_prompt},
            *[
                {"role": "assistant" if m.role == faction_2_id else "user", "content": m.message}
                for m in chats
            ],
        ]
    
    # print(messages)

    stream = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages,
        stream=True,
    )

    # def test_gen():
    #     from time import sleep

    #     for c in ['This', ' is', ' a', ' test', ' generator!']:
    #         sleep(0.5)
    #         yield c
    
    # stream = test_gen()

    for chunk in stream:
        if chunk:
            content = chunk.choices[0].delta.content
            # content = chunk
            # print("LLM TOKEN:", content)

            if content:
                # SSE FORMAT!
                yield f"event: llm\ndata: {content}\n\n"

    yield "event: done\ndata: none"

    # Return the full message
    return ''.join([chunk.choices[0].delta.content for chunk in stream])

def note_taker(game_id: str, faction_1_id: str, faction_2_id: str, messages: List[Message], storage: Storage) -> None:
    game_state = storage.get_game_state(game_id)

    prompt = load_prompt('note_taker')
    game_rules = load_gamerules()
    context = storage.get_context(game_id)
    ambassador_notes = storage.get_faction_interactions(game_id, faction_1_id, faction_2_id)
    
    f1 = get_faction(game_state.factions, faction_1_id)
    f2 = get_faction(game_state.factions, faction_2_id)

    situtation = '### Situation\nPlayer and other faction'
    game_rules_section = f"### Game Rules\n{game_rules}\n"
    faction_1_section = f"### Player faction\n{f1.name} (faction name) {f1.faction_id} (faction_id)\n"
    faction_2_section = f"### Bot faction\n{f2.name} (faction name) {f2.faction_id} (faction_id)\n"
    context_section = f"### Game Context (Lore)\n{context}\n"
    ambassador_notes_section = f"### Notes from previous turns\n{ambassador_notes}\n"
    message_section = f"### Mesagges\n{'\n'.join([m.message for m in messages])}"

    system_prompt = '\n'.join([prompt, situtation, game_rules_section, \
                               faction_1_section, faction_2_section, context_section, \
                            ambassador_notes_section, message_section
                            ])

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": system_prompt
        },
        {
            'role': 'user',
            'content': 'Take notes from the converstation with my advisor, please keep any important information and note action points'
        }]
    )

    new_notes = completion.choices[0].message.content

    storage.set_faction_interactions(game_id, faction_1_id, faction_2_id, new_notes or '')