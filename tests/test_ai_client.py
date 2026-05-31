from app.ai_client import AIClient
from app.ai_provider import ModelConfig, OpenAICompatibleAdapter


def test_ai_client_without_api_key_returns_static_safe_fallback():
    client = AIClient(api_key="")

    summary = client.summarize_pr("Fix docs", "", "", "README.md (modified, +1/-0)")
    file_review = client.review_file("README.md", "@@ -1 +1 @@\n+hello", "", "", "")
    cross_review = client.cross_file_analysis({"README.md": "hello"})

    assert summary["one_line_summary"]
    assert summary["focus_files"] == ["README.md"]
    assert file_review["findings"] == []
    assert cross_review["findings"] == []


def test_ai_client_limits_completion_tokens_for_provider_stability():
    client = AIClient(api_key="")

    class FakeCompletions:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs

            class Message:
                content = '{"ok": true}'

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    fake = FakeClient()
    config = ModelConfig(
        provider="openai-compatible",
        detected_provider="openai-compatible",
        api_key="secret",
        base_url="https://compat.example.com/v1",
        model=client.model,
        deep_model=client.deep_model,
        timeout_seconds=20,
        max_tokens=800,
    )
    client.adapter = OpenAICompatibleAdapter(config, sdk_client=fake)

    assert client._call_llm("system", "user") == '{"ok": true}'
    assert fake.chat.completions.kwargs["max_tokens"] > 0
    assert fake.chat.completions.kwargs["model"] == client.model


def test_ai_client_provider_error_falls_back_safely():
    client = AIClient(api_key="")

    class BrokenCompletions:
        def create(self, **kwargs):
            raise TimeoutError("provider timed out")

    class BrokenChat:
        completions = BrokenCompletions()

    class BrokenClient:
        chat = BrokenChat()

    config = ModelConfig(
        provider="openai-compatible",
        detected_provider="openai-compatible",
        api_key="secret",
        base_url="https://compat.example.com/v1",
        model=client.model,
        deep_model=client.deep_model,
        timeout_seconds=20,
        max_tokens=800,
    )
    client.adapter = OpenAICompatibleAdapter(config, sdk_client=BrokenClient())

    summary = client.summarize_pr("Fix auth", "", "", "app/auth.py (modified, +2/-1)")
    file_review = client.review_file("app/auth.py", "@@\n+pass", "", "", "")

    assert summary["one_line_summary"] == "Fix auth"
    assert summary["focus_files"] == ["app/auth.py"]
    assert file_review["file_summary"].startswith("AI review unavailable")
    assert file_review["findings"] == []
