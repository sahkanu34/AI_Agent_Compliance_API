"""
app/utils/config.py
Application settings loaded from .env
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    openai_temperature: float = 0.0
    openai_max_tokens: int = 4096

    data_dir: str = "data"
    output_dir: str = "outputs"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
