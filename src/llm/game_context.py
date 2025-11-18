
from files.local import LocalStorage
from llm.client import client
from llm.llm_game_state import process
from llm.helper_func import load_prompt, load_gamerules
from server.schema import GameUpdateList

def init_game_context(game_id: str, storage: LocalStorage) -> None:

    prompt = load_prompt('init_context')
    gamerules = load_gamerules()

    game_state_yaml = process(
        storage.get_game_state(game_id)
    )

    create_request = '\n'.join([prompt, gamerules, game_state_yaml])

    completion = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[
                    {
                        'role': "system",
                        "content": "Generate the lore based on the user prompt"
                    },
                    {
                        'role': 'user',
                        'content': create_request
                    }
            ]
        )

    context = completion.choices[0].message.content
    # context = 'blank context'

    storage.set_context(game_id, context)

def update_game_context(game_id: str, updates: GameUpdateList, storage: LocalStorage) -> None:

    prompt = load_prompt('update_game_state')
    game_rules = load_gamerules()

    game_state = storage.get_game_state(game_id)

    game_state_yaml = process(game_state)

    game_context = storage.get_context(game_id)

    faction_advisor_notes = '\n'.join([
        f'{f.faction_id}\n{storage.get_advisor_notes(game_id, f.faction_id)}'
        for f in game_state.factions if not f.available
    ])

    game_rules_section = f"### Game Rules\n{game_rules}\n"
    game_state_section = f"### Game State\n{game_state_yaml}\n"
    context_section = f"### Previous Game Context (Lore)\n{game_context}\n"
    advisor_notes_section = f"### Notes for each faction from their conversations with an advisor\n{faction_advisor_notes}\n"
    updates_section = f"### Updates to the game {updates.model_dump_json()}"

    system_prompt = '\n'.join([prompt, game_rules_section, \
                               game_state_section, context_section, \
                            advisor_notes_section, updates_section
                            ])

    completion = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[
                    {
                        'role': "system",
                        "content": system_prompt
                    },
                    {
                        'role': 'user',
                        'content': "Please fufill this request."
                    }
            ]
        )

    context = completion.choices[0].message.content
    # context = 'blank context'

    storage.set_context(game_id, context)