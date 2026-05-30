"""Tests for github_client.py — PR URL parsing."""

import pytest
import httpx
from app.github_client import GitHubClient


def test_parse_standard_pr_url():
    owner, repo, number = GitHubClient.parse_pr_url(
        "https://github.com/owner/repo/pull/123"
    )
    assert owner == "owner"
    assert repo == "repo"
    assert number == 123


def test_parse_pr_url_with_trailing_slash():
    owner, repo, number = GitHubClient.parse_pr_url(
        "https://github.com/owner/repo/pull/456/"
    )
    assert owner == "owner"
    assert repo == "repo"
    assert number == 456


def test_parse_pr_url_invalid():
    with pytest.raises(ValueError):
        GitHubClient.parse_pr_url("https://github.com/owner/repo")
    with pytest.raises(ValueError):
        GitHubClient.parse_pr_url("not a url")
    with pytest.raises(ValueError):
        GitHubClient.parse_pr_url("")


def test_get_changed_files_uses_authenticated_contents_api_with_head_sha(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code
            self.text = "raw fallback"

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=30, **kwargs):
        calls.append({"url": url, "headers": headers or {}, "timeout": timeout})
        if url.endswith("/pulls/3/files"):
            return FakeResponse([
                {
                    "filename": "app/service.py",
                    "status": "modified",
                    "additions": 2,
                    "deletions": 1,
                    "patch": "@@ -1,1 +1,2 @@\n+print('x')",
                    "raw_url": "https://raw.githubusercontent.com/acme/repo/old/app/service.py",
                }
            ])
        if "/contents/app/service.py?ref=abc123" in url:
            return FakeResponse({"content": "ZnJvbSBoZWFkIHNoYQo="})
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("app.github_client.httpx.get", fake_get)

    client = GitHubClient(token="token-123")
    files = client.get_changed_files("acme", "repo", 3, head_sha="abc123")

    assert files[0].raw_content == "from head sha\n"
    contents_call = next(c for c in calls if "/contents/app/service.py?ref=abc123" in c["url"])
    assert contents_call["headers"]["Authorization"] == "Bearer token-123"
    assert all("raw.githubusercontent.com" not in c["url"] for c in calls)


def test_get_changed_files_falls_back_to_public_diff_when_api_is_forbidden(monkeypatch):
    class FakeResponse:
        def __init__(self, payload=None, text="", status_code=200):
            self._payload = payload
            self.text = text
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", "https://api.github.com/repos/acme/repo/pulls/7/files")
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError("forbidden", request=request, response=response)

        def json(self):
            return self._payload

    diff = """diff --git a/app/service.py b/app/service.py
index 1111111..2222222 100644
--- a/app/service.py
+++ b/app/service.py
@@ -1,2 +1,3 @@
 def run():
+    password = "secret"
     return True
"""

    def fake_get(url, headers=None, timeout=30, **kwargs):
        if url.endswith("/pulls/7/files"):
            return FakeResponse(status_code=403)
        if url == "https://github.com/acme/repo/pull/7.diff":
            assert kwargs.get("follow_redirects") is True
            return FakeResponse(text=diff)
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("app.github_client.httpx.get", fake_get)

    files = GitHubClient().get_changed_files("acme", "repo", 7)

    assert len(files) == 1
    assert files[0].file_path == "app/service.py"
    assert files[0].change_type == "modified"
    assert files[0].additions == 1
    assert 'password = "secret"' in files[0].patch


def test_get_pr_info_falls_back_to_minimal_public_pr_info(monkeypatch):
    class FakeResponse:
        status_code = 403

        def raise_for_status(self):
            request = httpx.Request("GET", "https://api.github.com/repos/acme/repo/pulls/7")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    def fake_get(url, headers=None, timeout=30, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("app.github_client.httpx.get", fake_get)

    pr = GitHubClient().get_pr_info("acme", "repo", 7)

    assert pr.owner == "acme"
    assert pr.repo == "repo"
    assert pr.number == 7
    assert pr.title == "Public PR acme/repo#7"
