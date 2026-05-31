from app.report_generator import Report, ReportGenerator


def test_github_comment_contains_stable_idempotency_marker():
    report = Report(risk_level="LOW", merge_suggestion="safe")

    comment = ReportGenerator.generate_github_comment(report)

    assert "<!-- ai-review-cockpit-comment -->" in comment
