from typing import Tuple

def get_faction_order(faction_1_id: str, faction_2_id: str) -> Tuple[str]:

    first_faction, second_faction = max(faction_1_id, faction_2_id), min(faction_1_id, faction_2_id)

    return (first_faction, second_faction)