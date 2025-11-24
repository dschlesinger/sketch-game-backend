from typing import List

from files.general import Storage
from files.local import LocalStorage
from files.schema import Message
from llm.advisor import advisor

def init_faction_relationships(game_id: str, faction_ids: List[str], storage: Storage) -> None:

    for i, f1 in enumerate(faction_ids):
        for f2 in faction_ids[i + 1 : ]:
            storage.set_faction_interactions(game_id, f1, f2, '')

def message_faction(game_id: str, faction_1_id: str, faction_2_id: str, message: str, storage: LocalStorage):
    """f1 to f2
    """

    # Load message history
    messages = storage.get_messages(game_id, faction_1_id, faction_2_id)

    m = Message(
        role=faction_1_id,
        message=message
    )

    messages.append(m)

    # Can only be f2, as f1 initiates
    if faction_2_id == 'advisor':
        message = yield from advisor(game_id, faction_1_id, [m.message for m in messages], storage)
        return
    
