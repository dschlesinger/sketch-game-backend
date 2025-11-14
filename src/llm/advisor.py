from typing import List, Literal, AsyncGenerator

from pydantic import BaseModel

from llm.client import client
from llm.helper_func import load_prompt

class AdvisorMessage(BaseModel):
    role: Literal['player', 'advisor']

    message: str

# Streaming
async def advisor(faction_id: str, chats: List[AdvisorMessage]) -> AsyncGenerator:

    system_prompt = load_prompt('advisor')

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                'role': 'system',
                'content': system_prompt
            },
            *[{
                'role': ('user' if m.role == 'player' else 'assistant'),
                'content': m.message
            } for m in chats]
        ],
        stream=True,
    )

    async for chunk in stream:
        content = chunk.choices[0].delta.get("content")

        yield content