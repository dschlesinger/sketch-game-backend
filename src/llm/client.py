from openai import OpenAI

from server.settings import settings

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=settings.OPEN_ROUTER_KEY,
)