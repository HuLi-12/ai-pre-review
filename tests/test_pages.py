from fastapi.testclient import TestClient
import json

from app.database import SessionLocal
from app.models import PRReviewFinding, PRReviewTask
from main import app


def test_static_pages_render():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/rules").status_code == 200


def test_ui_uses_lighter_cockpit_theme():
    base_html = open("templates/base.html", encoding="utf-8").read()
    cockpit_css = open("static/css/cockpit.css", encoding="utf-8").read()

    assert 'data-bs-theme="light"' in base_html
    assert "--cockpit-bg: #F6F8FB;" in cockpit_css
    assert "--cockpit-card: #FFFFFF;" in cockpit_css


def test_home_page_shows_golden_evaluation_metrics():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Golden Evaluation" in response.text
    assert "Precision" in response.text
    assert "Recall" in response.text
    assert "False Positives" in response.text
    assert "20 cases" in response.text
    assert "Open Evaluation Dashboard" in response.text
    assert "Try public PR sample" in response.text


def test_golden_evaluation_api_returns_metrics():
    with TestClient(app) as client:
        response = client.get("/api/evaluation/golden")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] >= 20
    assert payload["precision"] == 1.0
    assert payload["recall"] == 1.0
    assert payload["false_positive_count"] == 0
    assert payload["false_negative_count"] == 0
    assert payload["rule_metrics"]["S005"]["expected"] == 2


def test_real_pr_replay_api_returns_metrics_and_sources():
    with TestClient(app) as client:
        response = client.get("/api/evaluation/real-pr-replay")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] >= 5
    assert payload["precision"] == 1.0
    assert payload["cases"][0]["source_url"].startswith("https://github.com/")
    assert "finding_evidence" in payload["cases"][0]


def test_evaluation_page_shows_rule_metrics_and_gate_comparison():
    with TestClient(app) as client:
        response = client.get("/evaluation")

    assert response.status_code == 200
    assert "Golden Evaluation Dashboard" in response.text
    assert "Ordinary diff-to-LLM baseline" in response.text
    assert "Baseline Candidates" in response.text
    assert "Evidence Gate Retention" in response.text
    assert "Invalid Model Output" in response.text
    assert "Synthetic Golden Cases" in response.text
    assert "Real PR Replay Cases" in response.text
    assert "Rule-level Quality" in response.text
    assert "S005" in response.text
    assert "20 cases" in response.text
    assert "localtunnel/localtunnel#339" in response.text


def test_report_page_shows_cockpit_vs_plain_llm_gate():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=1,
            pr_url="https://github.com/demo/repo/pull/1",
            status="DONE",
            risk_level="LOW",
            raw_finding_count=10,
            deduped_finding_count=6,
            visible_finding_count=4,
            github_ready_count=2,
            invalid_finding_count=3,
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(f"/tasks/{task_id}/report")

    assert response.status_code == 200
    assert "Cockpit Quality Gate" in response.text
    assert "Plain diff-to-LLM" in response.text
    assert "10 raw" in response.text
    assert "3 invalid" in response.text
    assert "2 comment-ready" in response.text

    with TestClient(app) as client:
        api_response = client.get(f"/api/tasks/{task_id}/report")

    assert api_response.status_code == 200
    assert api_response.json()["invalid_finding_count"] == 3


def test_report_page_highlights_changed_line_evidence():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=2,
            pr_url="https://github.com/demo/repo/pull/2",
            status="DONE",
            risk_level="HIGH",
            raw_finding_count=1,
            deduped_finding_count=1,
            visible_finding_count=1,
            github_ready_count=1,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        finding = PRReviewFinding(
            task_id=task.id,
            file_path="app/service.py",
            line_number=42,
            finding_type="correctness",
            severity="high",
            title="Missing null check before dereference",
            reason="The changed line dereferences user without a guard.",
            suggestion="Check user before returning user.name.",
            confidence=0.82,
            evidence_json=json.dumps([
                {"type": "ai_source", "label": "AI Source", "content": "ai_file"},
                {"type": "code_snippet", "label": "Code", "content": "return user.name"},
                {
                    "type": "confidence_reason",
                    "label": "Confidence Reason",
                    "content": "AI finding anchored to changed-line evidence",
                },
            ]),
        )
        db.add(finding)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(f"/tasks/{task_id}/report")

    assert response.status_code == 200
    assert "Changed-line Evidence" in response.text
    assert "return user.name" in response.text
    assert "Confidence Reason" in response.text
    assert "AI finding anchored to changed-line evidence" in response.text
    assert "Review Source" in response.text
    assert "ai_file" in response.text
