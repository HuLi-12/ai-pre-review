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
