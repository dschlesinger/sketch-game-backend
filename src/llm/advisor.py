from typing import List, Literal, Generator

from pydantic import BaseModel

from llm.client import client
from llm.helper_func import load_prompt

class AdvisorMessage(BaseModel):
    role: Literal['player', 'advisor']

    message: str

# Streaming
def advisor(faction_id: str, chats: List[AdvisorMessage]):
    system_prompt = load_prompt('advisor')

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            *[
                {"role": "user" if m.role == "player" else "assistant", "content": m.message}
                for m in chats
            ],
        ],
        stream=True,
    )

    for chunk in stream:
        if chunk:
            content = chunk.choices[0].delta.content
            print("LLM TOKEN:", content)

            if content:
                # SSE FORMAT!
                yield f"data: {content}\n\n"
