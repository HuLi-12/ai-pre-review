from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import PRReviewTask
from main import app


def test_static_pages_render():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/rules").status_code == 200


def test_home_page_shows_golden_evaluation_metrics():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Golden Evaluation" in response.text
    assert "Precision" in response.text
    assert "Recall" in response.text
    assert "False Positives" in response.text
    assert "8 cases" in response.text


def test_golden_evaluation_api_returns_metrics():
    with TestClient(app) as client:
        response = client.get("/api/evaluation/golden")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 8
    assert payload["precision"] == 1.0
    assert payload["recall"] == 1.0
    assert payload["false_positive_count"] == 0
    assert payload["false_negative_count"] == 0


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
    assert "2 comment-ready" in response.text
