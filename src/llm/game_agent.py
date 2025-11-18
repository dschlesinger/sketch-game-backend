from typing import List

from files.local import LocalStorage
from llm.client import client
from llm.helper_func import load_gamerules, load_prompt
from llm.llm_game_state import process
from llm.agent_tools import AGENT_TOOLS

def end_of_turn_update(game_id: str, storage: LocalStorage) -> List:
    
    prompt = load_prompt('end_of_turn')
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
    context_section = f"### Game Context (Lore)\n{game_context}\n"
    advisor_notes_section = f"### Notes for each faction from their conversations with an advisor\n{faction_advisor_notes}\n"

    system_prompt = '\n'.join([prompt, game_rules_section, \
                               game_state_section, context_section, \
                            advisor_notes_section
                            ])

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": system_prompt
        },
        {
            'role': 'user',
            'content': 'complete the end of turn, use as many tools as you think are needed'
        }],
        tools=AGENT_TOOLS
    )

    choice = completion.choices[0].message
    updates = []

    if hasattr(choice, "tool_calls") and choice.tool_calls:
        for tool_call in choice.tool_calls:
            tool_name = tool_call.function.name
            args = tool_call.function.arguments
            print(f"[TOOL CALL] {tool_name}({args})")
            # updates.extend(apply_tool_call(tool_name, json.loads(args), game_state))

        return choice.tool_calls