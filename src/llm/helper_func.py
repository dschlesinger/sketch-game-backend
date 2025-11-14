
def load_prompt(agent: str) -> str:
    path = f'agent_prompts/{agent}.txt'

    with open(path, 'r') as f:
        text = f.read()

    return text