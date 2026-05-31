from app.review_engine import ReviewEngine
from app.database import SessionLocal
from app.models import PRReviewTask
from app.static_scanner import RuleFinding


def test_s015_project_test_gap_survives_merge_filter():
    engine = ReviewEngine.__new__(ReviewEngine)
    findings = {
        "(project)": [
            RuleFinding(
                file_path="(project-wide)",
                line_number=0,
                rule_id="S015",
                severity="medium",
                message="Core source files changed but no test files were updated - consider adding tests",
            )
        ]
    }

    merged = engine._merge_findings([], [], findings)

    assert len(merged) == 1
    assert merged[0]["type"] == "S015"
    assert merged[0]["confidence"] >= 0.60


def test_static_rule_merge_preserves_code_snippet_for_evidence():
    engine = ReviewEngine.__new__(ReviewEngine)
    findings = {
        "app/auth.py": [
            RuleFinding(
                file_path="app/auth.py",
                line_number=12,
                rule_id="S005",
                severity="critical",
                message="Hardcoded password or secret detected",
                line_content='password = "secret123"',
            )
        ]
    }

    merged = engine._merge_findings([], [], findings)

    assert len(merged) == 1
    assert merged[0]["line_content"] == 'password = "secret123"'
    assert merged[0]["confidence_reason"] == "Deterministic static rule match with changed-line evidence"


def test_ai_file_finding_without_changed_line_evidence_is_filtered():
    engine = ReviewEngine.__new__(ReviewEngine)
    engine._changed_line_index = {
        "app/service.py": {
            10: "return user.name",
        }
    }
    ai_findings = [
        {
            "file": "app/service.py",
            "line": 90,
            "type": "correctness",
            "severity": "high",
            "title": "Possible null dereference",
            "reason": "The model claims this line may dereference None, but the cited line is outside the changed hunk.",
            "suggestion": "Move the check near the changed branch before dereferencing the object.",
            "confidence": 0.9,
        }
    ]

    merged = engine._merge_findings(ai_findings, [], {})

    assert merged == []


def test_ai_file_finding_near_changed_line_gets_evidence_bonus():
    engine = ReviewEngine.__new__(ReviewEngine)
    engine._changed_line_index = {
        "app/service.py": {
            42: "return user.name",
        }
    }
    ai_findings = [
        {
            "file": "app/service.py",
            "line": 43,
            "type": "correctness",
            "severity": "high",
            "title": "Missing null check before dereference",
            "reason": "The changed return path dereferences user.name without checking whether user can be None.",
            "suggestion": "Check user before returning user.name or raise a clear domain error.",
            "confidence": 1.5,
        }
    ]

    merged = engine._merge_findings(ai_findings, [], {})

    assert len(merged) == 1
    assert merged[0]["changed_line_evidence"] is True
    assert merged[0]["line_content"] == "return user.name"
    assert merged[0]["model_confidence"] == 1.0
    assert "changed-line evidence" in merged[0]["confidence_reason"]


def test_invalid_ai_file_findings_are_filtered_before_merge():
    engine = ReviewEngine.__new__(ReviewEngine)
    engine._changed_line_index = {
        "app/service.py": {
            42: "return user.name",
        }
    }
    ai_findings = [
        {
            "file": "app/service.py",
            "line": 42,
            "type": "correctness",
            "severity": "urgent",
            "title": "Invalid severity should be rejected",
            "reason": "This has enough text but an invalid severity enum.",
            "suggestion": "Use a supported severity value.",
            "confidence": 0.9,
        },
        {
            "file": "app/service.py",
            "line": 42,
            "type": "correctness",
            "severity": "high",
            "title": "Missing confidence should be rejected",
            "reason": "This has enough text but lacks a required model confidence field.",
            "suggestion": "Return confidence as a number between zero and one.",
        },
    ]

    merged = engine._merge_findings(ai_findings, [], {})

    assert merged == []
    assert engine._pipeline_counts["invalid"] == 2


def test_ai_file_finding_normalization_trims_text_and_lowercases_severity():
    engine = ReviewEngine.__new__(ReviewEngine)
    engine._changed_line_index = {
        "app/service.py": {
            42: "return user.name",
        }
    }
    ai_findings = [
        {
            "file": " app/service.py ",
            "line": "42",
            "type": "correctness",
            "severity": "HIGH",
            "title": "  Missing null check  ",
            "reason": "  The changed return path dereferences user.name without checking whether user can be None.  ",
            "suggestion": "  Check user before returning user.name or raise a clear domain error.  ",
            "confidence": "-0.2",
        }
    ]

    merged = engine._merge_findings(ai_findings, [], {})

    assert len(merged) == 1
    assert merged[0]["file"] == "app/service.py"
    assert merged[0]["line"] == 42
    assert merged[0]["severity"] == "high"
    assert merged[0]["title"] == "Missing null check"
    assert merged[0]["model_confidence"] == 0.0
    assert engine._pipeline_counts["invalid"] == 0


def test_review_engine_reuses_latest_comment_id_for_same_pr():
    db = SessionLocal()
    try:
        old_task = PRReviewTask(
            repo_owner="comment-reuse",
            repo_name="repo",
            pr_number=42,
            pr_url="https://github.com/comment-reuse/repo/pull/42",
            status="DONE",
            comment_id=98765,
        )
        new_task = PRReviewTask(
            repo_owner="comment-reuse",
            repo_name="repo",
            pr_number=42,
            pr_url="https://github.com/comment-reuse/repo/pull/42",
            status="PENDING",
        )
        db.add(old_task)
        db.add(new_task)
        db.commit()

        engine = ReviewEngine.__new__(ReviewEngine)

        assert engine._find_reusable_comment_id(new_task, db) == 98765
    finally:
        db.close()
