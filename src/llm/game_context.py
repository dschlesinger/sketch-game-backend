
from files.local import LocalStorage
from llm.client import client
from llm.llm_game_state import process
from llm.helper_func import load_prompt, load_gamerules

def init_game_context(game_id: str, storage: LocalStorage) -> None:

    prompt = load_prompt('init_context')
    gamerules = load_gamerules()

    game_state_yaml = process(
        storage.get_game_state(game_id)
    )

    create_request = '\n'.join([prompt, gamerules, game_state_yaml])

    # completion = client.chat.completions.create(
    #     model="google/gemini-2.5-pro",
    #     messages=[
    #                 {
    #                     'role': "system",
    #                     "content": "Generate the lore based on the user prompt"
    #                 },
    #                 {
    #                     'role': 'user',
    #                     'content': create_request
    #                 }
    #         ]
    #     )

    # context = completion.choices[0].message.content
    context = 'blank context'

    storage.set_context(game_id, context)

