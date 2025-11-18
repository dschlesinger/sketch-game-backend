AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_to_army",
            "description": "Add troops to an army, using the army id, numbers should be postive",
            "parameters": {
                "type": "object",
                "properties": {
                    "army_id": {"type": "string"},
                    "numbers": {"type": "integer"}
                },
                "required": ["army_id", "numbers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "subtract_from_army",
            "description": "Subtract troops from an army using army id, numbers should be negative",
            "parameters": {
                "type": "object",
                "properties": {
                    "army_id": {"type": "string"},
                    "numbers": {"type": "integer"}
                },
                "required": ["army_id", "numbers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_army",
            "description": "Move an army to another province using the army's id and the provinces id",
            "parameters": {
                "type": "object",
                "properties": {
                    "army_id": {"type": "string"},
                    "province_id": {"type": "string"}
                },
                "required": ["army_id", "province_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "new_army",
            "description": "Create a new army, can be used for splitting troops or rebellions or etc, faction_id of new army owner, province_id of where to start, and numbers must be a postive int",
            "parameters": {
                "type": "object",
                "properties": {
                    "faction_id": {"type": "string"},
                    "province_id": {"type": "string"},
                    "numbers": {"type": "integer"},
                },
                "required": ["army_id", "province_id", "numbers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "province_capture",
            "description": "Transfer a province from one faction to another, using the province id and the new factions id",
            "parameters": {
                "type": "object",
                "properties": {
                    "faction_id": {"type": "string"},
                    "province_id": {"type": "string"},
                },
                "required": ["province_id", "numbers"]
            }
        }
    }
]