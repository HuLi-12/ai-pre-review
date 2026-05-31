from fastapi.testclient import TestClient

from config import settings
from main import app


def test_system_status_exposes_safe_runtime_configuration(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "ai_api_key", "secret-key")
    monkeypatch.setattr(settings, "ai_api_base", "https://api.deepseek.com/v1")
    monkeypatch.setattr(settings, "ai_model", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "ai_deep_model", "deepseek-v4-flash")

    with TestClient(app) as client:
        response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()

    assert "ai" in payload
    assert "github" in payload
    assert payload["ai"]["provider"] in {"deepseek", "openai-compatible", "openai"}
    assert payload["ai"]["protocol"] == "openai-compatible-chat-completions"
    assert payload["ai"]["api_key_configured"] is True
    assert payload["ai"]["model"]
    assert payload["ai"]["deep_model"]
    assert payload["ai"]["timeout_seconds"] > 0
    assert payload["ai"]["max_tokens"] > 0
    assert "api_key" not in payload["ai"]
    assert "token" not in payload["github"]


def test_system_status_respects_manual_provider_override(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai-compatible")
    monkeypatch.setattr(settings, "ai_api_base", "https://api.deepseek.com/v1")

    with TestClient(app) as client:
        response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ai"]["provider"] == "openai-compatible"
    assert payload["ai"]["detected_provider"] == "deepseek"


def test_home_page_shows_ai_runtime_status(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "ai_api_key", "secret-key")
    monkeypatch.setattr(settings, "ai_api_base", "https://api.deepseek.com/v1")
    monkeypatch.setattr(settings, "ai_model", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "ai_deep_model", "deepseek-v4-flash")

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "AI Runtime" in response.text
    assert "deepseek-v4-flash" in response.text
    assert "OpenAI-compatible" in response.text
    assert "Key configured" in response.text
