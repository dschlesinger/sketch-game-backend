import json
from dataclasses import dataclass, field
from typing import List

from game.schema import GameState, Faction, City, Army, Fort, Port, Province


# --- JSON Loading Function (Unchanged) ---

def create_game_state_from_json(json_string: str) -> GameState:
    """
    Parses a JSON string and "hydrates" it into the full
    GameState object with all nested dataclasses.
    """
    data = json.loads(json_string)
    
    hydrated_factions = [Faction(**f_data) for f_data in data['factions']]
    
    hydrated_provinces = []
    for p_data in data['provinces']:
        p_copy = p_data.copy()
        if p_copy.get('city'):
            p_copy['city'] = City(**p_copy['city'])
        if p_copy.get('army'):
            p_copy['army'] = [Army(**a) for a in p_copy['army']]
        if p_copy.get('fort'):
            p_copy['fort'] = Fort(**p_copy['fort'])
        if p_copy.get('port'):
            p_copy['port'] = Port(**p_copy['port'])
        hydrated_provinces.append(Province(**p_copy))

    return GameState(
        name=data['name'],
        game_id=data['game_id'],
        owner=data['owner'],
        game_over=data['game_over'],
        factions=hydrated_factions,
        provinces=hydrated_provinces
    )

# --- NEW: Manual YAML Generation Function (No imports) ---

def generate_game_state_yaml_manual(game_state: GameState) -> str:
    """
    Converts the entire GameState into a token-efficient, YAML-formatted string
    using manual string building, with no external libraries.
    
    All 'id' fields are truncated (e.g., 'p_01' -> '01').
    """
    
    # 1. Create Look-up Maps for de-normalization
    faction_lookup = {f.faction_id: f.name for f in game_state.factions}
    
    province_name_lookup = {}
    for p in game_state.provinces:
        province_name_lookup[p.province_id] = "Ocean" if p.is_ocean else p.name

    # 2. Build the YAML string line by line
    
    # Use a list to accumulate lines, then join at the end.
    yaml_lines = []
    
    # --- Game State Header ---
    # yaml_lines.append(f"game_id: {game_state.game_id}")
    # yaml_lines.append(f"owner: {game_state.owner}")
    yaml_lines.append(f"game_over: {str(game_state.game_over).lower()}")

    # --- Faction Summary ---
    yaml_lines.append("factions:")
    for f in game_state.factions:
        yaml_lines.append(f"  - id: {f.faction_id}")
        yaml_lines.append(f"    name: {f.name}")
        yaml_lines.append(f"    defeated: {str(f.defeated).lower()}")
        # yaml_lines.append(f"    turn_ended: {str(f.turn_ended).lower()}")

    # --- Province List ---
    yaml_lines.append("provinces:")
    for p in game_state.provinces:
        yaml_lines.append(f"  - id: {p.province_id}")

        # --- Details ---
        p_name = province_name_lookup.get(p.province_id, "Unknown")
        if p.is_ocean:
            yaml_lines.append("    type: Ocean")
        else:
            yaml_lines.append("    type: Land")
            yaml_lines.append(f"    name: {p_name}")
            yaml_lines.append(f"    owner: {faction_lookup.get(p.faction_id, 'Neutral')}")

        # --- Contents (as a simple, token-light list) ---
        contents_list = []
        if p.city:
            contents_list.append("Capital City" if p.city.is_capital else "City")
        if len(p.army) > 0:
            for a in p.army:
                army_owner = faction_lookup.get(a.faction_id, "Unknown")
                unit_type = "Fleet" if p.is_ocean else "Army"
                contents_list.append(f"{unit_type} ({army_owner}): {a.numbers} (army id: {a.army_id})")
        if p.fort:
            contents_list.append("Fort")
        if p.port:
            contents_list.append("Port")
        
        if contents_list:
            yaml_lines.append("    contents:")
            for item in contents_list:
                yaml_lines.append(f"      - {item}")

        # --- Neighbors (as a simple, de-normalized list) ---
        neighbor_list = []
        for n_id in p.neighbors:
            n_name = province_name_lookup.get(n_id, "Unknown")
            n_id_truncated = n_id
            neighbor_list.append(f"{n_name} ({n_id_truncated})") # e.g., "Latium (01)"
        
        if neighbor_list:
            yaml_lines.append("    neighbors:")
            for item in neighbor_list:
                yaml_lines.append(f"      - {item}")

    # 3. Join all lines into a single string
    return "\n".join(yaml_lines)

def process(GAME_STATE_JSON_STRING: str | GameState) -> str:

    if not isinstance(GAME_STATE_JSON_STRING, GameState):
        # 1. Load the GameState from the JSON string
        game = create_game_state_from_json(GAME_STATE_JSON_STRING)
    else:
        game = GAME_STATE_JSON_STRING

    # 2. Generate and Print the new YAML
    yaml_output = generate_game_state_yaml_manual(game)
    return yaml_output