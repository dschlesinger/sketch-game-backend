from typing import Dict

from game.schema import get_faction
from game.end_turn import endturn
from files.general import Storage
from server.manager import ConnectionManager
from server.schema import GameUpdate, GameUpdateList
from llm.advisor import note_taker as ad_note_taker
from llm.ambassador import note_taker as amb_note_taker

async def route_websocket(game_id: str, faction_id: str, route: str, payload: Dict, manager: ConnectionManager, storage: Storage) -> None:

    match route:

        case 'endturn':

            # Get game state
            game_state = storage.get_game_state(game_id)

            player_faction = get_faction(game_state.factions, faction_id)
            
            # Save notes for advisor and all bot factions spoken to
            messages = storage.get_messages(game_id, faction_id, 'advisor')
            ad_note_taker(game_id, faction_id, messages, storage)
            
            # Delete Messages
            storage.set_messages(game_id, faction_id, 'advisor', [])
            
            for f in game_state.factions:
                
                if f.available:
                    
                    messages = storage.get_messages(game_id, faction_id, f.faction_id)
                    
                    if len(messages) > 0:
                        
                        amb_note_taker(game_id, faction_id, f.faction_id, messages, storage)
            
                        # Delete messages
                        storage.set_messages(game_id, faction_id, f.faction_id, [])


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

        

