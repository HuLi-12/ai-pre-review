from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    github_token: str = ""
    github_api_base: str = "https://api.github.com"

    ai_api_key: str = ""
    ai_api_base: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_deep_model: str = "gpt-4o"

    database_url: str = "sqlite:///./ai_review.db"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
