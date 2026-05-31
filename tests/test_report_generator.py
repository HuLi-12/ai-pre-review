from app.report_generator import Report, ReportGenerator


def test_github_comment_contains_stable_idempotency_marker():
    report = Report(risk_level="LOW", merge_suggestion="safe")

    comment = ReportGenerator.generate_github_comment(report)

    assert "<!-- ai-review-cockpit-comment -->" in comment


def test_github_comment_respects_github_ready_flag():
    """generate_github_comment should only include findings with github_ready=True."""
    findings = {
        "critical": [
            {"file": "src/app.py", "line": 42, "severity": "critical", "title": "SQL注入",
             "reason": "拼接SQL", "suggestion": "使用参数化", "confidence": 0.85,
             "github_ready": True, "type": "S014"},
            {"file": "src/app.py", "line": 55, "severity": "critical", "title": "硬编码密码",
             "reason": "明文密码", "suggestion": "使用环境变量", "confidence": 0.65,
             "github_ready": False, "type": "S005"},
        ],
        "high": [],
        "medium": [],
        "low": [],
    }
    report = Report(risk_level="HIGH", merge_suggestion="fix before merge",
                    key_focus_points=["SQL注入"], findings_by_severity=findings)

    comment = ReportGenerator.generate_github_comment(report)

    # Should include the github_ready finding (S014, conf=0.85)
    assert "SQL注入" in comment
    assert "S014" in comment

    # Should NOT include the non-github_ready finding (S005, conf=0.65)
    assert "硬编码密码" not in comment


def test_github_comment_all_filtered_shows_fallback_message():
    """When all findings exist but none are github_ready, show fallback message."""
    findings = {
        "medium": [
            {"file": "src/lib.py", "line": 10, "severity": "medium", "title": "小问题",
             "reason": "风格问题", "suggestion": "格式化", "confidence": 0.62,
             "github_ready": False, "type": "S007"},
        ],
        "critical": [],
        "high": [],
        "low": [],
    }
    report = Report(risk_level="LOW", merge_suggestion="safe",
                    findings_by_severity=findings)

    comment = ReportGenerator.generate_github_comment(report)

    assert "均未达到 GitHub 评论置信标准" in comment
    assert "小问题" not in comment


def test_github_comment_no_findings():
    """With zero findings total, show no-issues message."""
    report = Report(risk_level="LOW", merge_suggestion="safe")

    comment = ReportGenerator.generate_github_comment(report)

    assert "未发现明显问题" in comment


def test_github_comment_includes_evidence_summary():
    """High-severity github_ready findings should include evidence/reason."""
    findings = {
        "critical": [
            {"file": "src/db.py", "line": 20, "severity": "critical",
             "title": "Unsafe DELETE", "reason": "DELETE without WHERE clause",
             "suggestion": "Add WHERE condition", "confidence": 0.85,
             "github_ready": True, "type": "S014"},
        ],
        "high": [],
        "medium": [],
        "low": [],
    }
    report = Report(risk_level="CRITICAL", merge_suggestion="block merge",
                    key_focus_points=["Unsafe DELETE"], findings_by_severity=findings)

    comment = ReportGenerator.generate_github_comment(report)

    assert "Unsafe DELETE" in comment
    assert "DELETE without WHERE" in comment
    assert "S014" in comment


def test_github_comment_includes_actionable_suggestion_for_ready_findings():
    """GitHub-ready findings should include the concrete fix suggestion, not only the issue title."""
    findings = {
        "critical": [
            {"file": "src/db.py", "line": 20, "severity": "critical",
             "title": "Unsafe DELETE", "reason": "DELETE without WHERE clause",
             "suggestion": "Add a WHERE clause scoped to the target user id.", "confidence": 0.85,
             "github_ready": True, "type": "S014"},
        ],
        "high": [],
        "medium": [],
        "low": [],
    }
    report = Report(risk_level="CRITICAL", merge_suggestion="block merge",
                    key_focus_points=["Unsafe DELETE"], findings_by_severity=findings)

    comment = ReportGenerator.generate_github_comment(report)

    assert "建议" in comment
    assert "Add a WHERE clause scoped to the target user id." in comment
