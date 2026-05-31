from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    github_token: str = ""
    github_api_base: str = "https://api.github.com"

    ai_provider: str = "auto"
    ai_api_key: str = ""
    ai_api_base: str = Field(
        "https://api.openai.com/v1",
        validation_alias=AliasChoices("AI_API_BASE", "AI_BASE_URL"),
    )
    ai_model: str = "gpt-4o-mini"
    ai_deep_model: str = "gpt-4o"
    ai_timeout_seconds: float = 45.0
    ai_max_tokens: int = 1600

    database_url: str = "sqlite:///./ai_review.db"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


settings = Settings()
