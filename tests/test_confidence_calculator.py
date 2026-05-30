"""Tests for confidence_calculator.py — confidence thresholds."""

from app.confidence_calculator import (
    calculate_confidence,
    should_show_in_report,
    should_comment_to_github,
)


def test_s005_always_high():
    """S005 hardcoded_password should always have high confidence."""
    conf = calculate_confidence({"type": "S005", "source": "static_rule", "severity": "critical"})
    assert conf == 0.85
    assert should_show_in_report(conf) is True
    assert should_comment_to_github(conf, "critical") is True


def test_s014_always_high():
    """S014 unsafe_delete should always have high confidence."""
    conf = calculate_confidence({"type": "S014", "source": "static_rule", "severity": "critical"})
    assert conf == 0.85
    assert should_show_in_report(conf) is True


def test_well_documented_ai_finding():
    conf = calculate_confidence({
        "source": "ai_file",
        "file": "app.py",
        "line": 42,
        "reason": "Missing null check on user input that could cause NullPointerException",
        "suggestion": "Add if user is not None: check before processing",
        "severity": "high",
    })
    assert conf >= 0.80
    assert should_comment_to_github(conf, "high") is True


def test_poor_finding_hidden():
    conf = calculate_confidence({
        "source": "ai_file",
        "file": "",
        "line": 0,
        "reason": "short",
        "suggestion": "",
        "severity": "low",
    })
    assert conf < 0.60
    assert should_show_in_report(conf) is False


def test_agreement_bonus():
    base = calculate_confidence({
        "source": "ai_file",
        "file": "app.py",
        "line": 10,
        "reason": "Some issue with the code that needs attention",
        "suggestion": "Fix the issue by adding proper handling",
        "severity": "medium",
    }, has_rule_match=False)
    with_agreement = calculate_confidence({
        "source": "ai_file",
        "file": "app.py",
        "line": 10,
        "reason": "Some issue with the code that needs attention",
        "suggestion": "Fix the issue by adding proper handling",
        "severity": "medium",
    }, has_rule_match=True)
    assert with_agreement > base


def test_static_rule_high():
    conf = calculate_confidence({"type": "S001", "source": "static_rule", "severity": "high"})
    assert conf == 0.65
    assert should_show_in_report(conf) is True


def test_static_rule_low():
    conf = calculate_confidence({"type": "S002", "source": "static_rule", "severity": "low"})
    assert conf < 0.60
    assert should_show_in_report(conf) is False


def test_s015_test_missing_is_visible_project_signal():
    """S015 is project-level test coverage evidence and should not be hidden by default."""
    conf = calculate_confidence({
        "type": "S015",
        "source": "static_rule",
        "severity": "medium",
        "file": "(project-wide)",
        "line": 0,
        "reason": "Core source files changed but no test files were updated.",
        "suggestion": "Add focused tests for the changed source logic.",
    })
    assert conf >= 0.60
    assert should_show_in_report(conf) is True
