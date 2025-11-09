from llm.client import client

def get_advice(faction_id, context, state, scratch_pad, message) -> str:

    completion = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[
                    {
                        "role": "system",
                        "content": f"""You are an advising agent in a 2D strategy game. Reference the context section for more information about the game. Your job is to talk with your assigned faction {faction_id} and advise them on the state of the game. Your output will be sent back to the user. Keep messages informative but do not exceed 4 sentences unless extensive context is required

                            ### User message
                            {message}

                            ### Game Context
                            {context}

                            ### Game State
                            {state}

                            ### Advisor Scratch Pad, based on previous conversations
                            {scratch_pad}
                            """
                    },
                    ]
    )

    return completion.choices[0].message.content

def update_scratch_pad(faction_id, context, state, scratch_pad, message) -> str:

    completion = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[
                    {
                        "role": "system",
                        "content": f"""You are a scribe in a 2D strategy game that servers faction {faction_id}. Your job is to update the advisor scratch pad after
                        every interaction. Note all important agenda points, keep record of anything from the previous scratch pad that is important. Keep the notes brief.

                            ### User message
                            {message}

                            ### Game Context
                            {context}

                            ### Game State
                            {state}

                            ### Advisor Scratch Pad, based on previous conversations
                            {scratch_pad}

                            The previous scratch pad will be throw out make sure to reiterate any important information
                            """
                    },
                    ]
    )

    return completion.choices[0].message.content