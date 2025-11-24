from typing import List, Literal, Generator

from pydantic import BaseModel

from game.schema import get_faction
from files.local import LocalStorage
from files.schema import Message
from llm.client import client
from llm.llm_game_state import process
from llm.helper_func import load_prompt, load_gamerules

def init_advising_notes(game_id: str, faction_ids: List[str], storage: LocalStorage) -> None:

    for f in faction_ids:

        storage.set_advisor_notes(game_id, f.faction_id, '')

# Streaming
def advisor(game_id: str, faction_id: str, chats: List[Message], storage: LocalStorage):
    advisor_prompt = load_prompt('advisor')
    game_rules = load_gamerules()
    game_state = storage.get_game_state(game_id)
    game_state_yaml = process(game_state)
    context = storage.get_context(game_id)
    advisor_notes = storage.get_advisor_notes(game_id, faction_id)

    f = get_faction(game_state.factions, faction_id)

    game_rules_section = f"### Game Rules\n{game_rules}\n"
    faction_section = f"### Faction\nYou are advising faction {f.name} (faction name) {faction_id} (faction_id)\n"
    game_state_section = f"### Game State\n{game_state_yaml}\n"
    context_section = f"### Game Context (Lore)\n{context}\n"
    advisor_notes_section = f"### Notes from previous sessions\n{advisor_notes}\n"

    system_prompt = '\n'.join([advisor_prompt, game_rules_section, faction_section, \
                               game_state_section, context_section, advisor_notes_section
                            ])
    
    messages = [
            {"role": "system", "content": system_prompt},
            *[
                {"role": "assistant" if m.role == "advisor" else "user", "content": m.message}
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

    note_taking_conv = [
        f"{m.role}: {m.message}" for m in chats
    ]

    note_taker(game_id, faction_id, note_taking_conv, storage)

    yield "event: done\ndata: none"

    # Return the full message
    return ''.join([chunk.choices[0].delta.content for chunk in stream])

def note_taker(game_id: str, faction_id: str, messages: List, storage: LocalStorage) -> None:

    game_state = storage.get_game_state(game_id)

    f = get_faction(game_state.factions, faction_id)

    prompt = load_prompt('note_taker')
    game_rules = load_gamerules()
    context = storage.get_context(game_id)
    advisor_notes = storage.get_advisor_notes(game_id, faction_id)

    game_rules_section = f"### Game Rules\n{game_rules}\n"
    faction_section = f"### Faction\nAdvising  for faction {f.name} (faction name) {faction_id} (faction_id)\n"
    context_section = f"### Game Context (Lore)\n{context}\n"
    advisor_notes_section = f"### Notes from previous sessions\n{advisor_notes}\n"
    message_section = f"### Mesagges\n{'\n'.join(messages)}"

    system_prompt = '\n'.join([prompt, game_rules_section, \
                               faction_section, context_section, \
                            advisor_notes_section, message_section
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

    storage.set_advisor_notes(game_id, faction_id, new_notes)