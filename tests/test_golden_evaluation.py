from app.golden_evaluation import get_golden_cases, run_golden_evaluation


def test_golden_cases_cover_core_review_behaviors():
    cases = get_golden_cases()
    case_ids = {case.case_id for case in cases}

    assert len(cases) == 8
    assert {
        "hardcoded_secret",
        "unsafe_delete",
        "n_plus_one_loop",
        "fastapi_endpoint_missing_controls",
        "source_change_without_tests",
        "debug_print",
        "docs_fastapi_example_control",
        "safe_sql_where_control",
    } == case_ids


def test_run_golden_evaluation_quantifies_quality_and_confidence_gates():
    report = run_golden_evaluation()

    assert report.total_cases == 8
    assert report.expected_total == 7
    assert report.true_positive_count == 7
    assert report.false_negative_count == 0
    assert report.false_positive_count == 0
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.visible_expected_count == 7
    assert report.github_ready_count >= 2

    docs_case = next(case for case in report.cases if case.case_id == "docs_fastapi_example_control")
    assert docs_case.unexpected_rule_ids == []
    assert docs_case.detected_rule_ids == []
