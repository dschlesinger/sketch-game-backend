from typing import Generator, List

from server.manager import ConnectionManager
from game.schema import get_faction
from files.general import Storage
from files.schema import Message
from llm.advisor import advisor
from llm.ambassador import ambassador

def init_messages(game_id: str, factions: List[str], storage: Storage) -> None:
    
    for i, f1 in enumerate(factions):
        storage.set_messages(game_id, f1, 'advisor', [])
        for f2 in factions[i + 1 : ]:
            storage.set_messages(game_id, f1, f2, [])

def message_faction(game_id: str, faction_1_id: str, faction_2_id: str, message: str, manager: ConnectionManager, storage: Storage) -> Generator:
    """f1 to f2
    """

    # Load message history
    messages = storage.get_messages(game_id, faction_1_id, faction_2_id)

    m = Message(
        role=faction_1_id,
        message=message
    )

    messages.append(m)
    
    # This is acceptable for now as required down stream
    # Will link later
    game_state = storage.get_game_state(game_id)

    faction2 = get_faction(game_state.factions, faction_2_id)

    # Can only be f2, as f1 initiates
    if faction_2_id == 'advisor':
        message = yield from advisor(game_id, faction_1_id, messages, storage)
        messages.append(
            Message(
                role=faction_2_id,
                message=message
            )
        )

    # If faction 2 is a bot
    elif faction2.available:
        
        if faction2 is None:
            print(f'Unknown faction {faction_2_id} in {game_id}')
        
        message = yield from ambassador(game_id, faction_1_id, faction_1_id, messages, storage)
        
        messages.append(
            Message(
                role=faction_2_id,
                message=message
            )
        )
    else:
        # Is a human
        manager.send_message(game_id, faction_2_id, m)

    # Add user message and return message if bot or advisor    
    storage.set_messages(game_id, faction_1_id, faction_2_id, messages)