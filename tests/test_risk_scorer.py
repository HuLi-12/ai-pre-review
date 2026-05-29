"""Tests for risk_scorer.py — file risk scoring."""

from app.risk_scorer import FileRiskScorer
from app.github_client import ChangedFile


def test_readme_is_low_risk():
    scorer = FileRiskScorer()
    f = ChangedFile("README.md", "modified", 5, 2, "docs update", "content")
    result = scorer.score(f)
    assert result["level"] == "LOW"
    assert scorer.should_skip(f) is True


def test_service_is_medium_or_high():
    scorer = FileRiskScorer()
    f = ChangedFile("app/services/user_service.py", "modified", 50, 10, "patch", "content")
    result = scorer.score(f)
    assert result["score"] >= 3  # service keyword = +3
    assert result["level"] in ("MEDIUM", "HIGH")


def test_controller_is_medium():
    scorer = FileRiskScorer()
    f = ChangedFile("src/controller/UserController.java", "modified", 30, 5, "patch", "content")
    result = scorer.score(f)
    assert result["level"] in ("MEDIUM", "HIGH")


def test_large_addition_increases_score():
    scorer = FileRiskScorer()
    small = ChangedFile("app/core.py", "modified", 10, 0, "patch", "content")
    large = ChangedFile("app/core.py", "modified", 300, 0, "patch", "content")
    assert scorer.score(small)["score"] < scorer.score(large)["score"]


def test_risky_keyword_increases_score():
    scorer = FileRiskScorer()
    normal = ChangedFile("app/core.py", "modified", 10, 0, "normal code", "content")
    risky = ChangedFile("app/core.py", "modified", 10, 0, "password = 'secret'", "content")
    assert scorer.score(normal)["score"] < scorer.score(risky)["score"]


def test_get_analysis_depth():
    scorer = FileRiskScorer()
    readme = ChangedFile("README.md", "modified", 2, 1, "docs", "content")
    service = ChangedFile("app/service/core.py", "modified", 100, 20, "patch", "content")
    assert scorer.get_analysis_depth(readme) == "skip"
    assert scorer.get_analysis_depth(service) in ("normal", "deep")
