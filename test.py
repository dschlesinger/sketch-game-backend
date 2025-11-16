from files.local import LocalStorage
from llm.llm_game_state import process

storage = LocalStorage()

gs = storage.get_game_state('UWI52Q')

print(process(gs))