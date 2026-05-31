import json
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import PRReviewFinding, PRReviewTask
from main import app


def test_template_response_helper_supports_new_starlette_signature(monkeypatch):
    import main as main_module

    calls = []

    def fake_template_response(*args):
        calls.append(args)
        return "ok"

    request = object()
    monkeypatch.setattr(main_module.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr(main_module, "_REQUEST_FIRST_TEMPLATE_RESPONSE", True)

    assert main_module.render_template(request, "demo.html", {"value": 1}) == "ok"
    assert calls == [(request, "demo.html", {"value": 1, "request": request})]


def test_template_response_helper_supports_old_starlette_signature(monkeypatch):
    import main as main_module

    calls = []

    def fake_template_response(*args):
        calls.append(args)
        return "ok"

    request = object()
    monkeypatch.setattr(main_module.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr(main_module, "_REQUEST_FIRST_TEMPLATE_RESPONSE", False)

    assert main_module.render_template(request, "demo.html", {"value": 1}) == "ok"
    assert calls == [("demo.html", {"value": 1, "request": request})]


def test_static_pages_render():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/about").status_code == 200
        assert client.get("/rules").status_code == 200


def test_rules_page_presents_static_rules_as_evidence_not_limits():
    with TestClient(app) as client:
        response = client.get("/rules")

    assert response.status_code == 200
    assert "Static Rules" in response.text
    assert "Rules are evidence, not limits" in response.text
    assert "不代表 AI Review Cockpit 的全部 Review 能力" in response.text
    assert "AI File Review" in response.text
    assert "AI Cross-file Review" in response.text


def test_task_history_pr_main_link_points_to_internal_report():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=404,
            pr_url="https://github.com/demo/repo/pull/404",
            status="DONE",
            risk_level="LOW",
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/tasks")

    assert response.status_code == 200
    assert f'href="/tasks/{task_id}/report"' in response.text
    assert "打开 GitHub PR" in response.text


def test_task_history_marks_stale_active_tasks_as_failed():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=405,
            pr_url="https://github.com/demo/repo/pull/405",
            status="PENDING",
            progress=0,
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(hours=2),
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/tasks")

    assert response.status_code == 200
    assert "后台任务已中断" in response.text

    db = SessionLocal()
    try:
        refreshed = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
        assert refreshed.status == "FAILED"
        assert refreshed.error_type in {"STALE_TASK", "SERVER_RESTART"}
    finally:
        db.close()


def test_ui_uses_lighter_cockpit_theme():
    base_html = open("templates/base.html", encoding="utf-8").read()
    cockpit_css = open("static/css/cockpit.css", encoding="utf-8").read()

    assert 'data-bs-theme="light"' in base_html
    assert "--cockpit-bg: #F6F8FB;" in cockpit_css
    assert "--cockpit-card: #FFFFFF;" in cockpit_css


def test_home_page_is_minimal_review_entry():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "AI Review Cockpit" in response.text
    assert "输入 GitHub PR 链接，生成低噪声、可解释的 Review 报告" in response.text
    assert "GitHub PR 链接" in response.text
    assert "GitHub Token（可选）" in response.text
    assert "自动回写 GitHub 评论" in response.text
    assert "开始评审" in response.text
    assert "Changed Lines" in response.text
    assert "Evidence Chain" in response.text
    assert "Review Decision" in response.text
    assert "Golden Evaluation" in response.text

    assert "AI Runtime" not in response.text
    assert "Live Preview" not in response.text
    assert "工作流程" not in response.text
    assert "为什么不是普通 AI Review" not in response.text


def test_about_page_contains_product_explanations():
    with TestClient(app) as client:
        response = client.get("/about")

    assert response.status_code == 200
    assert "为什么不是普通 AI Review" in response.text
    assert "工作流程" in response.text
    assert "Changed Lines" in response.text
    assert "Risk-Aware Routing" in response.text
    assert "Confidence Gate" in response.text
    assert "Evidence Chain" in response.text
    assert "Review Decision" in response.text
    assert "未来扩展方向" in response.text


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
    assert "Golden Evaluation" in response.text
    assert "S005" in response.text
    assert "localtunnel/localtunnel#339" in response.text


def test_report_page_prioritizes_decision_and_collapses_details():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=1,
            pr_url="https://github.com/demo/repo/pull/1",
            status="DONE",
            risk_level="LOW",
            summary="本次 PR 主要调整接口参数校验。",
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
    assert "Risk Level" in response.text
    assert "Merge Decision" in response.text
    assert "Findings" in response.text
    assert "GitHub Ready" in response.text
    assert "PR Summary" in response.text
    assert "本次 PR 主要调整接口参数校验。" in response.text
    assert 'id="fileRiskMapCollapse" class="collapse"' in response.text
    assert 'id="pipelineCollapse" class="collapse"' in response.text
    assert "commentPreviewPanel" in response.text
    assert "data-preview-url" in response.text

    with TestClient(app) as client:
        api_response = client.get(f"/api/tasks/{task_id}/report")

    assert api_response.status_code == 200
    assert api_response.json()["invalid_finding_count"] == 3


def test_report_page_shows_high_findings_and_collapses_medium_low_by_default():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=2,
            pr_url="https://github.com/demo/repo/pull/2",
            status="DONE",
            risk_level="HIGH",
            raw_finding_count=2,
            deduped_finding_count=2,
            visible_finding_count=2,
            github_ready_count=1,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        high = PRReviewFinding(
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
        medium = PRReviewFinding(
            task_id=task.id,
            file_path="app/service.py",
            line_number=51,
            finding_type="testing",
            severity="medium",
            title="Missing tests for changed behavior",
            reason="The changed service path has no matching tests.",
            suggestion="Add regression tests.",
            confidence=0.66,
        )
        db.add_all([high, medium])
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(f"/tasks/{task_id}/report")

    assert response.status_code == 200
    assert 'id="collapse-high" class="collapse show"' in response.text
    assert 'id="collapse-medium" class="collapse"' in response.text
    assert "Missing null check before dereference" in response.text
    assert "Evidence Chain" in response.text
    assert "return user.name" in response.text
    assert "Confidence Reason" in response.text
    assert "AI finding anchored to changed-line evidence" in response.text


def test_report_page_distinguishes_static_and_ai_finding_sources():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=406,
            pr_url="https://github.com/demo/repo/pull/406",
            status="DONE",
            risk_level="HIGH",
            raw_finding_count=2,
            deduped_finding_count=2,
            visible_finding_count=2,
            github_ready_count=1,
        )
        db.add(task)
        db.commit()
        static_finding = PRReviewFinding(
            task_id=task.id,
            file_path="app/auth.py",
            line_number=12,
            finding_type="S005",
            severity="critical",
            title="Hardcoded password or secret detected",
            reason="A deterministic static rule matched a changed line.",
            suggestion="Move the secret to environment variables.",
            confidence=0.85,
            evidence_json=json.dumps([
                {"type": "review_source", "label": "Review Source", "content": "Static Rule S005"},
                {"type": "rule_match", "label": "Static Rule", "content": "S005"},
            ]),
        )
        ai_finding = PRReviewFinding(
            task_id=task.id,
            file_path="app/order_service.py",
            line_number=87,
            finding_type="correctness",
            severity="high",
            title="Order status update lacks transaction protection",
            reason="The AI semantic review found a transaction boundary risk.",
            suggestion="Put both updates in one transaction.",
            confidence=0.72,
            evidence_json=json.dumps([
                {"type": "review_source", "label": "Review Source", "content": "AI File Review correctness"},
                {"type": "ai_source", "label": "AI Source", "content": "ai_file"},
            ]),
        )
        db.add_all([static_finding, ai_finding])
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(f"/tasks/{task_id}/report")

    assert response.status_code == 200
    assert "Static Rule S005" in response.text
    assert "AI File Review correctness" in response.text


def test_report_page_hydrates_missing_static_rule_suggestion():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=407,
            pr_url="https://github.com/demo/repo/pull/407",
            status="DONE",
            risk_level="CRITICAL",
            raw_finding_count=1,
            deduped_finding_count=1,
            visible_finding_count=1,
            github_ready_count=1,
        )
        db.add(task)
        db.commit()
        db.add(PRReviewFinding(
            task_id=task.id,
            file_path="app/auth.py",
            line_number=12,
            finding_type="S005",
            severity="critical",
            title="Hardcoded password or secret detected",
            reason="A deterministic static rule matched a changed line.",
            suggestion="",
            confidence=0.85,
        ))
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(f"/tasks/{task_id}/report")

    assert response.status_code == 200
    assert "os.getenv" in response.text
    assert "Static Rule S005" in response.text


def test_comment_preview_hydrates_missing_static_rule_suggestion():
    db = SessionLocal()
    try:
        task = PRReviewTask(
            repo_owner="demo",
            repo_name="repo",
            pr_number=408,
            pr_url="https://github.com/demo/repo/pull/408",
            status="DONE",
            risk_level="CRITICAL",
            raw_finding_count=1,
            deduped_finding_count=1,
            visible_finding_count=1,
            github_ready_count=1,
        )
        db.add(task)
        db.commit()
        db.add(PRReviewFinding(
            task_id=task.id,
            file_path="app/auth.py",
            line_number=12,
            finding_type="S005",
            severity="critical",
            title="Hardcoded password or secret detected",
            reason="A deterministic static rule matched a changed line.",
            suggestion="",
            confidence=0.85,
        ))
        db.commit()
        task_id = task.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(f"/api/tasks/{task_id}/comment-preview")

    assert response.status_code == 200
    assert "os.getenv" in response.json()["comment_markdown"]
