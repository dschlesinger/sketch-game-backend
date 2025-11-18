from typing import List
import uuid

from game.schema import GameState, get_faction, get_province, get_army, remove_army_from_current_province, Army
from llm.game_agent import end_of_turn_update
from server.schema import GameUpdateList, GameUpdate
from files.local import LocalStorage

def endturn(game_id: str, game_state: GameState, storage: LocalStorage) -> GameUpdateList | None:

    tools = end_of_turn_update(game_id, storage)

    # Update gamestate on our end
    if tools:

        updates = tool_calls_to_updates(tools)

        update_game_state(game_state, updates.game_updates)

        return updates


def tool_calls_to_updates(tool_calls: List) -> GameUpdateList:

    updates = []

    for t in tool_calls:

        match t.function.name:

            case 'add_to_army':
                
                if t.function.arguments['numbers'] < 1:
                    print('tool call flawed', t)

                updates.append(
                    GameUpdate(
                        type='army_change',
                        props=t.function.arguments
                    )
                )

            case 'subtract_from_army':

                if t.function.arguments['numbers'] > -1:
                    print('tool call flawed', t)

                updates.append(
                    GameUpdate(
                        type='army_change',
                        props=t.function.arguments
                    )
                )

            case 'move_army':
                updates.append(
                    GameUpdate(
                        type='move_army',
                        props=t.function.arguments
                    )
                )

            case 'new_army':
                
                if t.function.arguments['numbers'] < 1:
                    print('tool call flawed', t)

                updates.append(
                    GameUpdate(
                        type='new_army',
                        props=t.function.arguments
                    )
                )

            case 'province_capture':
                
                updates.append(
                    GameUpdate(
                        type='province_change',
                        props=t.function.arguments
                    )
                )

            case _:

                print('tool not recognized', t)

    return GameUpdateList(game_updates=updates)

def update_game_state(game_state: GameState, updates: GameUpdateList) -> GameState:

    for u in updates:

        match u.type:

            case 'ended_turn':

                faction_id = u.props['faction_id']

                faction = get_faction(game_state.factions, faction_id)

                faction.turn_ended = u.props['turn_status']

            case 'game_turn':

                game_state.turn_status = u.props['status']

            case 'army_change':

                army_id = u.props['army_id']

                army = get_army(game_state.provinces, army_id)

                army.numbers += u.props['numbers']

            case 'province_change':

                faction_id = u.props['faction_id']
                province_id = u.props['province_id']

                p = get_province(game_state.provinces, province_id)

                p.faction_id = faction_id

            case 'move_army':

                army_id = u.props['army_id']
                province_id = u.props['province_id']

                a = remove_army_from_current_province(game_state.provinces, army_id)

                p = get_province(game_state.provinces, province_id)

                if a is not None:
                    p.army.append(a)
                else:
                    print('Could not find army to move')

            case 'new_army':

                numbers = u.props['numbers']
                province_id = u.props['province_id']
                faction_id = u.props['faction_id']

                army_id = str(uuid.uuid4()).split('-')[0]

                p = get_province(game_state.provinces, province_id)

                p.army.append(Army(
                    army_id=army_id,
                    faction_id=faction_id,
                    numbers=numbers
                ))

            case _:

                print('update unknown type', u)