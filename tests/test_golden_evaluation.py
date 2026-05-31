from app.golden_evaluation import (
    get_golden_cases,
    get_real_pr_replay_cases,
    run_golden_evaluation,
    run_real_pr_replay_evaluation,
)


def test_golden_cases_cover_core_review_behaviors():
    cases = get_golden_cases()
    case_ids = {case.case_id for case in cases}

    assert len(cases) >= 20
    assert {
        "hardcoded_secret",
        "unsafe_delete",
        "n_plus_one_loop",
        "fastapi_endpoint_missing_controls",
        "source_change_without_tests",
        "debug_print",
        "docs_fastapi_example_control",
        "safe_sql_where_control",
        "sensitive_log",
        "todo_comment",
        "broad_exception",
        "empty_js_catch",
        "unsafe_update",
        "safe_update_where_control",
        "console_log_js",
        "markdown_secret_control",
        "typescript_endpoint_missing_controls",
        "source_and_test_changed_control",
        "lockfile_only_control",
        "api_key_literal",
    }.issubset(case_ids)


def test_run_golden_evaluation_quantifies_quality_and_confidence_gates():
    report = run_golden_evaluation()

    assert report.total_cases >= 20
    assert report.expected_total >= 16
    assert report.true_positive_count == report.expected_total
    assert report.false_negative_count == 0
    assert report.false_positive_count == 0
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.visible_expected_count == report.expected_total
    assert report.github_ready_count >= 2
    assert report.baseline_candidate_count >= report.visible_finding_count
    assert report.raw_finding_count >= report.visible_finding_count
    assert report.invalid_finding_count == 0
    assert report.deduped_finding_count >= report.visible_finding_count
    assert report.evidence_backed_count == report.visible_finding_count
    assert report.evidence_gate_retention_rate == 1.0

    docs_case = next(case for case in report.cases if case.case_id == "docs_fastapi_example_control")
    assert docs_case.unexpected_rule_ids == []
    assert docs_case.detected_rule_ids == []
    assert docs_case.baseline_candidate_count == 0


def test_golden_evaluation_reports_rule_level_metrics():
    report = run_golden_evaluation()

    assert report.rule_metrics["S005"]["expected"] == 2
    assert report.rule_metrics["S005"]["true_positive"] == 2
    assert report.rule_metrics["S005"]["false_negative"] == 0
    assert report.rule_metrics["S005"]["precision"] == 1.0
    assert report.rule_metrics["S005"]["recall"] == 1.0
    assert report.rule_metrics["S014"]["expected"] == 2
    assert report.rule_metrics["S015"]["false_positive"] == 0


def test_real_pr_replay_cases_are_fixed_public_pr_snapshots():
    cases = get_real_pr_replay_cases()

    assert len(cases) >= 5
    assert all(case.source_url.startswith("https://github.com/") for case in cases)
    assert all(case.changed_files for case in cases)


def test_real_pr_replay_evaluation_reports_metrics_and_evidence():
    report = run_real_pr_replay_evaluation()

    assert report.total_cases >= 5
    assert report.precision == 1.0
    assert report.false_positive_count == 0
    assert "S015" in report.rule_metrics

    localtunnel_case = next(case for case in report.cases if case.case_id == "real_localtunnel_auth_pr")
    assert localtunnel_case.source_url == "https://github.com/localtunnel/localtunnel/pull/339"
    assert "S015" in localtunnel_case.detected_rule_ids
    assert localtunnel_case.finding_evidence
    assert localtunnel_case.finding_evidence[0]["gate"] in {"visible", "github_ready"}
    assert localtunnel_case.raw_finding_count >= localtunnel_case.visible_finding_count
    assert localtunnel_case.invalid_finding_count == 0
    assert localtunnel_case.evidence_backed_count == localtunnel_case.visible_finding_count
    assert "confidence_reason" in localtunnel_case.finding_evidence[0]
