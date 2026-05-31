from app.ai_provider import ModelConfig, OpenAICompatibleAdapter, build_model_config
from app.ai_client import AIClient


class FakeCompletions:
    def __init__(self, content='{"ok": true}', error=None):
        self.content = content
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error

        class Message:
            pass

        class Choice:
            pass

        class Response:
            pass

        message = Message()
        message.content = self.content
        choice = Choice()
        choice.message = message
        response = Response()
        response.choices = [choice]
        return response


class FakeSdkClient:
    def __init__(self, completions):
        self.chat = type("Chat", (), {"completions": completions})()


def test_openai_compatible_adapter_sends_stability_limits():
    completions = FakeCompletions()
    config = ModelConfig(
        provider="deepseek",
        detected_provider="deepseek",
        api_key="secret",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-flash",
        deep_model="deepseek-v4-flash",
        timeout_seconds=20,
        max_tokens=800,
    )
    adapter = OpenAICompatibleAdapter(config, sdk_client=FakeSdkClient(completions))

    assert adapter.complete("system", "user", model="deepseek-v4-flash") == '{"ok": true}'
    assert completions.kwargs["model"] == "deepseek-v4-flash"
    assert completions.kwargs["max_tokens"] == 800
    assert completions.kwargs["messages"][0]["role"] == "system"
    assert completions.kwargs["messages"][1]["role"] == "user"


def test_openai_compatible_adapter_returns_empty_on_provider_error():
    config = ModelConfig(
        provider="openai-compatible",
        detected_provider="openai-compatible",
        api_key="secret",
        base_url="https://compat.example.com/v1",
        model="fast",
        deep_model="strong",
        timeout_seconds=20,
        max_tokens=800,
    )
    adapter = OpenAICompatibleAdapter(
        config,
        sdk_client=FakeSdkClient(FakeCompletions(error=TimeoutError("slow"))),
    )

    assert adapter.complete("system", "user") == ""


def test_model_config_status_is_safe_and_provider_agnostic(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "ai_provider", "openai-compatible")
    monkeypatch.setattr(settings, "ai_api_key", "secret")
    monkeypatch.setattr(settings, "ai_api_base", "https://api.deepseek.com/v1")
    monkeypatch.setattr(settings, "ai_model", "fast")
    monkeypatch.setattr(settings, "ai_deep_model", "strong")

    config = build_model_config(settings)
    status = config.to_status()

    assert config.provider == "openai-compatible"
    assert config.detected_provider == "deepseek"
    assert status.protocol == "openai-compatible-chat-completions"
    assert status.api_key_configured is True
    assert not hasattr(status, "api_key")


def test_ai_client_uses_injected_adapter():
    class FakeAdapter:
        enabled = True
        config = ModelConfig(
            provider="openai-compatible",
            detected_provider="openai-compatible",
            api_key="secret",
            base_url="https://compat.example.com/v1",
            model="fast",
            deep_model="strong",
            timeout_seconds=20,
            max_tokens=800,
        )

        def __init__(self):
            self.calls = []

        def complete(self, system_prompt, user_prompt, model=None, temperature=0.1):
            self.calls.append((system_prompt, user_prompt, model, temperature))
            return '{"ok": true}'

    adapter = FakeAdapter()
    client = AIClient(adapter=adapter)

    assert client._call_llm("system", "user") == '{"ok": true}'
    assert adapter.calls == [("system", "user", None, 0.1)]
