from config import settings
from app.ai_provider import build_model_config


def build_system_status() -> dict:
    return {
        "ai": build_model_config(settings).to_status().to_dict(),
        "github": {
            "api_base": settings.github_api_base,
            "token_configured": bool(settings.github_token),
        },
        "database": {
            "engine": settings.database_url.split(":", 1)[0],
        },
    }
