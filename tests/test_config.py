from config import Settings


def test_settings_accepts_ai_api_base_env_name(monkeypatch):
    monkeypatch.setenv("AI_API_BASE", "https://api.deepseek.com/v1")
    monkeypatch.delenv("AI_BASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.ai_api_base == "https://api.deepseek.com/v1"


def test_settings_accepts_legacy_ai_base_url_env_name(monkeypatch):
    monkeypatch.delenv("AI_API_BASE", raising=False)
    monkeypatch.setenv("AI_BASE_URL", "https://compat.example.com/v1")

    settings = Settings(_env_file=None)

    assert settings.ai_api_base == "https://compat.example.com/v1"
