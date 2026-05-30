from app.review_engine import ReviewEngine
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
