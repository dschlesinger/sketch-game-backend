from typing import Dict

from game.schema import get_faction
from files.local import LocalStorage

async def route_websocket(game_id: str, faction_id: str, route: str, payload: Dict, storage: LocalStorage) -> None:

    match route:

        case 'endturn':

            # Get game state
            game_state = storage.get_game_state(game_id)

            player_faction = get_faction(game_state.factions, faction_id)

            player_faction.turn_ended = True

            # Check if all players turns are over
            all_turns_ended = all([f.available or f.turn_ended for f in game_state.factions])

            if all_turns_ended:

                print('All turns ended')

                for fi in game_state.factions:

                    fi.turn_ended = False

            storage.set_game_state(game_id, game_state)

        

