from app.golden_evaluation import get_golden_cases, run_golden_evaluation


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

    docs_case = next(case for case in report.cases if case.case_id == "docs_fastapi_example_control")
    assert docs_case.unexpected_rule_ids == []
    assert docs_case.detected_rule_ids == []


def test_golden_evaluation_reports_rule_level_metrics():
    report = run_golden_evaluation()

    assert report.rule_metrics["S005"]["expected"] == 2
    assert report.rule_metrics["S005"]["true_positive"] == 2
    assert report.rule_metrics["S005"]["false_negative"] == 0
    assert report.rule_metrics["S005"]["precision"] == 1.0
    assert report.rule_metrics["S005"]["recall"] == 1.0
    assert report.rule_metrics["S014"]["expected"] == 2
    assert report.rule_metrics["S015"]["false_positive"] == 0
