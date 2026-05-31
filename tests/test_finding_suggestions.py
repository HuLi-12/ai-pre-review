from app.database import SessionLocal
from app.finding_suggestions import hydrate_missing_suggestions
from app.models import PRReviewFinding, PRReviewTask
import json


def test_hydrate_missing_suggestions_does_not_dirty_db_session():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=409,
            pr_url="https://github.com/demo/repo/pull/409",
            status="DONE",
        )
        db.add(task)
        db.commit()
        finding = PRReviewFinding(
            task_id=task.id,
            file_path="app/auth.py",
            finding_type="S005",
            severity="critical",
            title="Hardcoded password or secret detected",
            suggestion="",
            confidence=0.85,
        )
        db.add(finding)
        db.commit()

        persisted = db.query(PRReviewFinding).filter(PRReviewFinding.id == finding.id).one()
        hydrate_missing_suggestions([persisted])

        assert "os.getenv" in persisted.suggestion
        assert persisted not in db.dirty
        assert not db.dirty
    finally:
        db.close()


def test_hydrate_missing_suggestions_adds_static_rule_review_source_without_dirtying_session():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=412,
            pr_url="https://github.com/demo/repo/pull/412",
            status="DONE",
        )
        db.add(task)
        db.commit()
        finding = PRReviewFinding(
            task_id=task.id,
            file_path="app/auth.py",
            finding_type="S005",
            severity="critical",
            title="Hardcoded password or secret detected",
            suggestion="",
            confidence=0.85,
            evidence_json=json.dumps([
                {"type": "rule_match", "label": "Static Rule", "content": "S005"},
            ]),
        )
        db.add(finding)
        db.commit()

        persisted = db.query(PRReviewFinding).filter(PRReviewFinding.id == finding.id).one()
        hydrate_missing_suggestions([persisted])
        evidence = json.loads(persisted.evidence_json)

        assert {"type": "review_source", "label": "Review Source", "content": "Static Rule S005"} in evidence
        assert persisted not in db.dirty
        assert not db.dirty
    finally:
        db.close()
