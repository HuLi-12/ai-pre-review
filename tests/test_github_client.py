"""Tests for github_client.py — PR URL parsing."""

import pytest
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
