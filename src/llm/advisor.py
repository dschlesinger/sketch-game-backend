from typing import List, Literal, Generator

from pydantic import BaseModel

from files.local import LocalStorage
from llm.client import client
from llm.llm_game_state import process
from llm.helper_func import load_prompt, load_gamerules

class AdvisorMessage(BaseModel):
    role: Literal['player', 'advisor']

    message: str

def init_advising_notes(game_id: str, faction_ids: List[str], storage: LocalStorage) -> None:

    for f in faction_ids:

        storage.set_advisor_notes(game_id, f.faction_id, '')

# Streaming
def advisor(game_id: str, faction_id: str, chats: List[AdvisorMessage], storage: LocalStorage):
    advisor_prompt = load_prompt('advisor')
    game_rules = load_gamerules()
    game_state_yaml = process(storage.get_game_state(game_id))
    context = storage.get_context(game_id)
    advisor_notes = storage.get_advisor_notes(game_id, faction_id)

    game_rules_section = f"### Game Rules\n{game_rules}\n"
    faction_section = f"### Faction\nYou are advising faction {faction_id} (faction_id)\n"
    game_state_section = f"### Game State\n{game_state_yaml}\n"
    context_section = f"### Game Context (Lore)\n{context}\n"
    advisor_notes_section = f"### Notes from previous sessions\n{advisor_notes}\n"

    system_prompt = '\n'.join([advisor_prompt, game_rules_section, faction_section, \
                               game_state_section, context_section, advisor_notes_section
                            ])
    
    messages = [
            {"role": "system", "content": system_prompt},
            *[
                {"role": "user" if m.role == "player" else "assistant", "content": m.message}
                for m in chats
            ],
        ]
    
    print(messages)

    stream = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        if chunk:
            content = chunk.choices[0].delta.content
            print("LLM TOKEN:", content)

            if content:
                # SSE FORMAT!
                yield f"event: llm\ndata: {content}\n\n"

    yield "event: done\ndata: none"
