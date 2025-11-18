from typing import Dict

from game.schema import get_faction
from game.end_turn import endturn
from files.local import LocalStorage
from server.manager import ConnectionManager
from server.schema import GameUpdate, GameUpdateList

async def route_websocket(game_id: str, faction_id: str, route: str, payload: Dict, manager: ConnectionManager, storage: LocalStorage) -> None:

    match route:

        case 'endturn':

            # Get game state
            game_state = storage.get_game_state(game_id)

            player_faction = get_faction(game_state.factions, faction_id)

            player_faction.turn_ended = True

            await manager.broadcast_updates(
                    game_id,
                    GameUpdateList(game_updates=[GameUpdate(
                            type='ended_turn',
                            props={
                                'faction_id': faction_id,
                                'turn_status': True
                            }
                    )])
                )

            # Check if all players turns are over
            all_turns_ended = all([f.available or f.turn_ended for f in game_state.factions])

            if all_turns_ended:

                print('All turns ended')

                await manager.broadcast_updates(
                    game_id,
                    GameUpdateList(game_updates=[GameUpdate(
                        type='game_turn',
                        props={
                            'status': 'editting_game_state'
                        }
                    )])
                )

                # Edit game state with agent
                updates = endturn(game_id, game_state, storage)

                # Update context

                unend_turn_updates = [] if updates is None else [*updates.game_updates]

                for fi in game_state.factions:

                    fi.turn_ended = False

                    unend_turn_updates.append(
                        GameUpdate(
                            type='ended_turn',
                            props={
                                'faction_id': fi.faction_id,
                                'turn_status': False
                            }
                        )
                    )

                await manager.broadcast_updates(
                    game_id=game_id,
                    updates=GameUpdateList(game_updates=unend_turn_updates)
                )



            storage.set_game_state(game_id, game_state)

        

