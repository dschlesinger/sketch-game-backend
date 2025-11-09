from dataclasses import dataclass, field
from typing import List, Dict, Literal, Optional
from pydantic import BaseModel
from llm.client import client

import json

from create_game.schema import GameState, get_province, Army, get_faction


# ==========================================================
# LLM TOOL INTERACTIONS
# ==========================================================

class Update(BaseModel):
    type: Literal["province", "faction"]
    id: str
    data: Dict


def apply_tool_call(tool_name: str, args: dict, game_state: GameState):
    updates = []

    match tool_name:
        # --------------------------------------------------
        # Add to Army
        # --------------------------------------------------
        case "add_to_army":
            p = get_province(game_state.provinces, args["province_id"])
            if not p:
                return updates

            if p.army is None:
                p.army = Army(faction_id=args.get("faction_id", p.faction_id), numbers=args["number"])
            else:
                p.army.numbers += args["number"]

            updates.append({
                "type": "province",
                "id": p.province_id,
                "data": p
            })

        # --------------------------------------------------
        # Subtract from Army
        # --------------------------------------------------
        case "subtract_from_army":
            p = get_province(game_state.provinces, args["province_id"])
            if not p or not p.army:
                return updates

            p.army.numbers -= args["number"]
            if p.army.numbers <= 0:
                p.army = None  # army destroyed

            updates.append({
                "type": "province",
                "id": p.province_id,
                "data": p
            })

        # --------------------------------------------------
        # Capture Province
        # --------------------------------------------------
        case "capture_province":
            province = get_province(game_state.provinces, args["province_id"])
            if not province:
                return updates

            old_faction_id = province.faction_id
            new_faction_id = args["faction_id"]
            province.faction_id = new_faction_id

            updates.append({
                "type": "province",
                "id": province.province_id,
                "data": province
            })

            if not old_faction_id:
                return updates

            old_faction = get_faction(game_state.factions, old_faction_id)
            if not old_faction:
                return updates

            # check if old faction still has a capital
            capital_captured = True
            for p in game_state.provinces:
                if p.faction_id == old_faction_id and p.city and p.city.is_capital:
                    capital_captured = False
                    break

            if capital_captured:
                # transfer all provinces of the defeated faction
                for p in game_state.provinces:
                    if p.faction_id == old_faction_id:
                        p.faction_id = new_faction_id
                        updates.append({
                            "type": "province",
                            "id": p.province_id,
                            "data": p
                        })
                old_faction.is_defeated = True
                updates.append({
                    "type": "faction",
                    "id": old_faction.faction_id,
                    "data": old_faction
                })

        # --------------------------------------------------
        case _:
            print(f"[WARN] Unknown tool: {tool_name}")

    return updates


# ==========================================================
# TURN PROCESSING
# ==========================================================

def process_turn_end(context: str, game_state_yaml: str, advisor_pads: List[str], game_state: GameState):
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a turn-processor for a turn-based strategy game. "
                           "You decide outcomes and call tools to modify the game state."
            },
            {
                "role": "user",
                "content": f"""
Process the end of a turn. Use the available tools to modify the game state.
Favor balance: assist smaller factions slightly, but remain fair.

### Game Context
{context}

### Game State
{game_state_yaml}

### Advisor Scratch Pads
{'----'.join(advisor_pads)}
"""
            }
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "add_to_army",
                    "description": "Add members to an army in a given region",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province_id": {"type": "string"},
                            "number": {"type": "integer"},
                            "faction_id": {"type": "string"}
                        },
                        "required": ["province_id", "number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "subtract_from_army",
                    "description": "Subtract members from an army in a given region",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province_id": {"type": "string"},
                            "number": {"type": "integer"}
                        },
                        "required": ["province_id", "number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "capture_province",
                    "description": "Transfer ownership of a province to a new faction",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province_id": {"type": "string"},
                            "faction_id": {"type": "string"}
                        },
                        "required": ["province_id", "faction_id"]
                    }
                }
            }
        ]
    )

    choice = completion.choices[0].message
    updates = []

    if hasattr(choice, "tool_calls") and choice.tool_calls:
        for tool_call in choice.tool_calls:
            tool_name = tool_call.function.name
            args = tool_call.function.arguments
            print(f"[TOOL CALL] {tool_name}({args})")
            updates.extend(apply_tool_call(tool_name, json.loads(args), game_state))
    else:
        print("No tool calls made by model.")
        print(choice.content)

    return updates

import json
from dataclasses import asdict
from typing import List, Dict

def update_game_state(s3, game_state: GameState, updates: List[Dict], bucket_name: str):
    """
    Apply updates to the game state and upload the updated version to S3 using a passed-in boto3 resource.

    Args:
        s3: boto3 S3 resource (e.g., boto3.resource("s3"))
        game_state (GameState): Current game state dataclass instance.
        updates (List[Dict]): List of updates returned from apply_tool_call().
        bucket_name (str): Name of the S3 bucket.
    """

    # --------------------------------------------------
    # Apply each update to the game state
    # --------------------------------------------------
    for update in updates:
        update_type = update["type"]
        update_id = update["id"]
        update_data = update["data"]

        match update_type:
            case "province":
                for i, province in enumerate(game_state.provinces):
                    if province.province_id == update_id:
                        game_state.provinces[i] = update_data
                        break

            case "faction":
                for i, faction in enumerate(game_state.factions):
                    if faction.faction_id == update_id:
                        game_state.factions[i] = update_data
                        break

            case _:
                print(f"[WARN] Unknown update type: {update_type}")

    # --------------------------------------------------
    # Serialize the updated game state
    # --------------------------------------------------
    game_state_json = json.dumps(asdict(game_state), indent=2)

    # --------------------------------------------------
    # Upload to S3 using resource
    # --------------------------------------------------
    bucket = s3.Bucket(bucket_name)
    key = f"game-state/game-state-{game_state.game_id}.json"
    bucket.put_object(Key=key, Body=game_state_json.encode("utf-8"))

    print(f"[UPLOAD] Updated game state uploaded to s3://{bucket_name}/{key}")

    return game_state

from llm.client import client

def update_context(s3, bucket_name: str, game_id: str, context: str, new_game_state_yaml: str, advisor_pads: List[str]):
    """
    Update the game context using Gemini and upload the new context to S3.

    Args:
        s3: boto3 S3 resource
        bucket_name (str): Name of the S3 bucket
        game_id (str): ID of the game
        context (str): Current game context
        new_game_state_yaml (str): YAML/string representation of the updated game state
        advisor_pads (List[str]): Advisor scratch pad notes
    Returns:
        str: Updated game context
    """

    # Prompt Gemini for updated context
    completion = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a context agent for a turn-based strategy game. "
                    "Update the game context based on the new game state and advisor notes."
                )
            },
            {
                "role": "user",
                "content": f"""
Current context:
{context}

Updated game state:
{new_game_state_yaml}

Advisor scratch pads:
{'----'.join(advisor_pads)}

Please provide a revised game context that incorporates all updates and is ready for the next turn.
"""
            }
        ]
    )

    updated_context = completion.choices[0].message.content

    # Upload updated context to S3
    bucket = s3.Bucket(bucket_name)
    key = f"context/context-{game_id}.txt"
    bucket.put_object(Key=key, Body=updated_context.encode("utf-8"))

    print(f"[UPLOAD] Updated context uploaded to s3://{bucket_name}/{key}")

    return updated_context

