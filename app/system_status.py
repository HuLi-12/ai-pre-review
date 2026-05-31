from urllib.parse import urlparse

from config import settings


SUPPORTED_AI_PROVIDERS = {"auto", "deepseek", "openai", "openai-compatible"}
AI_PROTOCOL = "openai-compatible-chat-completions"


def detect_ai_provider(base_url: str) -> str:
    host = urlparse(base_url).netloc.lower()
    if "deepseek" in host:
        return "deepseek"
    if "openai.com" in host:
        return "openai"
    return "openai-compatible"


def resolve_ai_provider(configured_provider: str, base_url: str) -> tuple[str, str]:
    configured = (configured_provider or "auto").strip().lower()
    if configured not in SUPPORTED_AI_PROVIDERS:
        configured = "openai-compatible"

    detected = detect_ai_provider(base_url)
    if configured == "auto":
        return detected, detected
    return configured, detected


def build_system_status() -> dict:
    provider, detected_provider = resolve_ai_provider(settings.ai_provider, settings.ai_api_base)
    return {
        "ai": {
            "provider": provider,
            "detected_provider": detected_provider,
            "protocol": AI_PROTOCOL,
            "base_url": settings.ai_api_base,
            "api_key_configured": bool(settings.ai_api_key),
            "model": settings.ai_model,
            "deep_model": settings.ai_deep_model,
            "timeout_seconds": settings.ai_timeout_seconds,
            "max_tokens": settings.ai_max_tokens,
        },
        "github": {
            "api_base": settings.github_api_base,
            "token_configured": bool(settings.github_token),
        },
        "database": {
            "engine": settings.database_url.split(":", 1)[0],
        },
    }
