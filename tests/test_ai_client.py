from app.ai_client import AIClient


def test_ai_client_without_api_key_returns_static_safe_fallback():
    client = AIClient(api_key="")

    summary = client.summarize_pr("Fix docs", "", "", "README.md (modified, +1/-0)")
    file_review = client.review_file("README.md", "@@ -1 +1 @@\n+hello", "", "", "")
    cross_review = client.cross_file_analysis({"README.md": "hello"})

    assert summary["one_line_summary"]
    assert summary["focus_files"] == ["README.md"]
    assert file_review["findings"] == []
    assert cross_review["findings"] == []
