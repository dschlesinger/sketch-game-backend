from typing import Literal

from pydantic import BaseModel

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    devolopment: bool

    OPEN_ROUTER_KEY: str

    BOTO3_ACCESS_KEY: str
    BOTO3_SECRET_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
