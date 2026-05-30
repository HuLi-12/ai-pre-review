"""Golden evaluation cases for the PR review engine.

The cases are intentionally local and deterministic so judging/demo runs can
measure review quality without depending on GitHub or an LLM provider.
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict

from app.github_client import ChangedFile
from app.review_engine import ReviewEngine
from app.static_scanner import RuleFinding, StaticScanner
from app.confidence_calculator import should_comment_to_github


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    title: str
    changed_files: List[ChangedFile]
    expected_rule_ids: Set[str]


@dataclass
class GoldenCaseResult:
    case_id: str
    title: str
    expected_rule_ids: List[str]
    detected_rule_ids: List[str]
    visible_rule_ids: List[str]
    github_ready_rule_ids: List[str]
    missing_rule_ids: List[str]
    unexpected_rule_ids: List[str]


@dataclass
class GoldenEvaluationReport:
    total_cases: int
    expected_total: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    visible_expected_count: int
    github_ready_count: int
    precision: float
    recall: float
    rule_metrics: Dict[str, Dict[str, float]]
    cases: List[GoldenCaseResult] = field(default_factory=list)


def get_golden_cases() -> List[GoldenCase]:
    return [
        GoldenCase(
            case_id="hardcoded_secret",
            title="Hardcoded secret in changed Python code",
            changed_files=[
                _file("app/auth_service.py", """@@ -1,3 +1,5 @@
 def login():
+    password = "secret123"
     return True
"""),
                _test_file("tests/test_auth_service.py"),
            ],
            expected_rule_ids={"S005"},
        ),
        GoldenCase(
            case_id="unsafe_delete",
            title="Unsafe SQL delete without WHERE",
            changed_files=[
                _file("app/user_repository.py", """@@ -1,3 +1,5 @@
 def cleanup():
+    db.execute("DELETE FROM users")
     return True
"""),
                _test_file("tests/test_user_repository.py"),
            ],
            expected_rule_ids={"S014"},
        ),
        GoldenCase(
            case_id="n_plus_one_loop",
            title="Database query inside loop",
            changed_files=[
                _file("app/order_service.py", """@@ -1,4 +1,8 @@
 def load_orders(ids):
+    results = []
+    for order_id in ids:
+        results.append(db.query(Order).get(order_id))
+    return results
"""),
                _test_file("tests/test_order_service.py"),
            ],
            expected_rule_ids={"S011"},
        ),
        GoldenCase(
            case_id="fastapi_endpoint_missing_controls",
            title="New FastAPI endpoint without auth and validation signals",
            changed_files=[
                _file("app/routes/admin.py", """@@ -1,3 +1,7 @@
 router = APIRouter()
+@router.post("/admin/delete")
+def delete_user(user_id: int):
+    return service.delete_user(user_id)
"""),
                _test_file("tests/test_admin_routes.py"),
            ],
            expected_rule_ids={"S008", "S009"},
        ),
        GoldenCase(
            case_id="source_change_without_tests",
            title="Core source change without any test file change",
            changed_files=[
                _file("app/payment_service.py", """@@ -1,3 +1,5 @@
 def charge(amount):
+    audit_log(amount)
     return gateway.charge(amount)
""")
            ],
            expected_rule_ids={"S015"},
        ),
        GoldenCase(
            case_id="debug_print",
            title="Debug print in production Python code",
            changed_files=[
                _file("app/billing_controller.py", """@@ -1,3 +1,5 @@
 def create_invoice(data):
+    print("debug invoice", data)
     return service.create_invoice(data)
"""),
                _test_file("tests/test_billing_controller.py"),
            ],
            expected_rule_ids={"S001"},
        ),
        GoldenCase(
            case_id="docs_fastapi_example_control",
            title="Documentation code example should not be reviewed as production code",
            changed_files=[
                _file("docs/advanced.md", """@@ -1,3 +1,8 @@
+```python
+@app.post("/users")
+def create_user(name: str):
+    return {"name": name}
+```
""")
            ],
            expected_rule_ids=set(),
        ),
        GoldenCase(
            case_id="safe_sql_where_control",
            title="Delete with explicit WHERE should not trigger unsafe SQL rule",
            changed_files=[
                _file("app/user_repository.py", """@@ -1,3 +1,5 @@
 def delete_user(user_id):
+    db.execute("DELETE FROM users WHERE id = :id", {"id": user_id})
     return True
"""),
                _test_file("tests/test_user_repository.py"),
            ],
            expected_rule_ids=set(),
        ),
        GoldenCase(
            case_id="sensitive_log",
            title="Password value logged in changed Python code",
            changed_files=[
                _file("app/session_service.py", """@@ -1,3 +1,5 @@
+import logging
def rotate_password(password):
+    logger.info("password changed: %s", password)
     return True
"""),
                _test_file("tests/test_session_service.py"),
            ],
            expected_rule_ids={"S004"},
        ),
        GoldenCase(
            case_id="todo_comment",
            title="TODO comment left in production code",
            changed_files=[
                _file("app/refund_service.py", """@@ -1,3 +1,5 @@
 def refund(order):
+    # TODO: bypass validation for now
     return gateway.refund(order)
"""),
                _test_file("tests/test_refund_service.py"),
            ],
            expected_rule_ids={"S002"},
        ),
        GoldenCase(
            case_id="broad_exception",
            title="Broad Java exception catch",
            changed_files=[
                _file("src/main/java/App.java", """@@ -1,3 +1,7 @@
+try {
+    processor.run();
+} catch (Exception e) {
+    return false;
+}
"""),
                _test_file("src/test/java/AppTest.java"),
            ],
            expected_rule_ids={"S010"},
        ),
        GoldenCase(
            case_id="empty_js_catch",
            title="Empty JavaScript catch block",
            changed_files=[
                _file("web/src/api.js", """@@ -1,3 +1,5 @@
 async function save() {
+  try { await api.save(); } catch (err) {}
 }
"""),
                _test_file("web/src/api.test.js"),
            ],
            expected_rule_ids={"S003"},
        ),
        GoldenCase(
            case_id="unsafe_update",
            title="Unsafe SQL update without WHERE",
            changed_files=[
                _file("app/account_repository.py", """@@ -1,3 +1,5 @@
 def reset_balances():
+    db.execute("UPDATE accounts SET balance = 0")
     return True
"""),
                _test_file("tests/test_account_repository.py"),
            ],
            expected_rule_ids={"S014"},
        ),
        GoldenCase(
            case_id="safe_update_where_control",
            title="Update with explicit WHERE should not trigger unsafe SQL rule",
            changed_files=[
                _file("app/account_repository.py", """@@ -1,3 +1,5 @@
 def reset_balance(account_id):
+    db.execute("UPDATE accounts SET balance = 0 WHERE id = :id", {"id": account_id})
     return True
"""),
                _test_file("tests/test_account_repository.py"),
            ],
            expected_rule_ids=set(),
        ),
        GoldenCase(
            case_id="console_log_js",
            title="Console log in production JavaScript code",
            changed_files=[
                _file("web/src/checkout.js", """@@ -1,3 +1,6 @@
 export function checkout(cart) {
+  console.log("checkout cart", cart);
   return api.checkout(cart);
+}
"""),
                _test_file("web/src/checkout.test.js"),
            ],
            expected_rule_ids={"S001"},
        ),
        GoldenCase(
            case_id="markdown_secret_control",
            title="Documentation secret-like example should not be treated as production code",
            changed_files=[
                _file("docs/secrets.md", """@@ -1,2 +1,5 @@
+# Example
+password = "secret123"
+api_key = "demo"
""")
            ],
            expected_rule_ids=set(),
        ),
        GoldenCase(
            case_id="typescript_endpoint_missing_controls",
            title="New TypeScript router endpoint without controls",
            changed_files=[
                _file("web/src/admin-routes.ts", """@@ -1,3 +1,7 @@
const router = createRouter();
+@router.post("/admin/archive")
+def archive_user(user_id: int):
+  return archiveUser(req.body.userId);
"""),
                _test_file("web/src/admin-routes.test.ts"),
            ],
            expected_rule_ids={"S008", "S009"},
        ),
        GoldenCase(
            case_id="source_and_test_changed_control",
            title="Source change with matching test should not trigger missing test rule",
            changed_files=[
                _file("app/invoice_service.py", """@@ -1,3 +1,5 @@
 def total(items):
+    audit_items(items)
     return sum(items)
"""),
                _test_file("tests/test_invoice_service.py"),
            ],
            expected_rule_ids=set(),
        ),
        GoldenCase(
            case_id="lockfile_only_control",
            title="Lockfile-only change should not trigger review findings",
            changed_files=[
                _file("package-lock.json", """@@ -1,3 +1,5 @@
 {
+  "lockfileVersion": 3,
   "packages": {}
 }
""")
            ],
            expected_rule_ids=set(),
        ),
        GoldenCase(
            case_id="api_key_literal",
            title="Hardcoded API key in TypeScript code",
            changed_files=[
                _file("web/src/client.ts", """@@ -1,3 +1,5 @@
 export const client = createClient({
+  apiKey = "sk-test-hardcoded"
 });
"""),
                _test_file("web/src/client.test.ts"),
            ],
            expected_rule_ids={"S005"},
        ),
    ]


def run_golden_evaluation(cases: Optional[List[GoldenCase]] = None) -> GoldenEvaluationReport:
    selected_cases = cases or get_golden_cases()
    case_results = [_evaluate_case(case) for case in selected_cases]

    expected_total = sum(len(case.expected_rule_ids) for case in selected_cases)
    true_positive_count = sum(len(result.expected_detected_rule_ids) for result in _internal_results(case_results))
    false_positive_count = sum(len(result.unexpected_rule_ids) for result in case_results)
    false_negative_count = sum(len(result.missing_rule_ids) for result in case_results)
    visible_expected_count = sum(len(result.expected_visible_rule_ids) for result in _internal_results(case_results))
    github_ready_count = sum(len(result.github_ready_rule_ids) for result in case_results)

    detected_total = true_positive_count + false_positive_count
    precision = round(true_positive_count / detected_total, 4) if detected_total else 1.0
    recall = round(true_positive_count / expected_total, 4) if expected_total else 1.0
    rule_metrics = _calculate_rule_metrics(case_results)

    return GoldenEvaluationReport(
        total_cases=len(selected_cases),
        expected_total=expected_total,
        true_positive_count=true_positive_count,
        false_positive_count=false_positive_count,
        false_negative_count=false_negative_count,
        visible_expected_count=visible_expected_count,
        github_ready_count=github_ready_count,
        precision=precision,
        recall=recall,
        rule_metrics=rule_metrics,
        cases=case_results,
    )


def _evaluate_case(case: GoldenCase) -> GoldenCaseResult:
    engine = ReviewEngine.__new__(ReviewEngine)
    engine.scanner = StaticScanner()
    rule_findings = ReviewEngine._run_static_scan(engine, case.changed_files)
    merged = ReviewEngine._merge_findings(engine, [], [], rule_findings)

    detected = _rule_ids_from_rule_findings(rule_findings)
    visible = {finding.get("type", "") for finding in merged}
    github_ready = {
        finding.get("type", "")
        for finding in merged
        if should_comment_to_github(finding.get("confidence", 0) or 0, finding.get("severity", "low"))
    }

    missing = case.expected_rule_ids - detected
    unexpected = detected - case.expected_rule_ids

    return GoldenCaseResult(
        case_id=case.case_id,
        title=case.title,
        expected_rule_ids=sorted(case.expected_rule_ids),
        detected_rule_ids=sorted(detected),
        visible_rule_ids=sorted(visible),
        github_ready_rule_ids=sorted(github_ready),
        missing_rule_ids=sorted(missing),
        unexpected_rule_ids=sorted(unexpected),
    )


@dataclass
class _InternalCaseMetrics:
    expected_detected_rule_ids: Set[str]
    expected_visible_rule_ids: Set[str]
    unexpected_rule_ids: Set[str]
    missing_rule_ids: Set[str]


def _internal_results(results: List[GoldenCaseResult]) -> List[_InternalCaseMetrics]:
    converted = []
    for result in results:
        expected = set(result.expected_rule_ids)
        detected = set(result.detected_rule_ids)
        visible = set(result.visible_rule_ids)
        converted.append(_InternalCaseMetrics(
            expected_detected_rule_ids=expected & detected,
            expected_visible_rule_ids=expected & visible,
            unexpected_rule_ids=set(result.unexpected_rule_ids),
            missing_rule_ids=set(result.missing_rule_ids),
        ))
    return converted


def _calculate_rule_metrics(results: List[GoldenCaseResult]) -> Dict[str, Dict[str, float]]:
    rule_ids = sorted({
        rule_id
        for result in results
        for rule_id in (
            result.expected_rule_ids
            + result.detected_rule_ids
            + result.missing_rule_ids
            + result.unexpected_rule_ids
        )
    })
    metrics: Dict[str, Dict[str, float]] = {}

    for rule_id in rule_ids:
        expected = 0
        true_positive = 0
        false_positive = 0
        false_negative = 0
        visible = 0
        github_ready = 0

        for result in results:
            expected_set = set(result.expected_rule_ids)
            detected_set = set(result.detected_rule_ids)
            visible_set = set(result.visible_rule_ids)
            github_ready_set = set(result.github_ready_rule_ids)
            unexpected_set = set(result.unexpected_rule_ids)
            missing_set = set(result.missing_rule_ids)

            if rule_id in expected_set:
                expected += 1
            if rule_id in expected_set and rule_id in detected_set:
                true_positive += 1
            if rule_id in unexpected_set:
                false_positive += 1
            if rule_id in missing_set:
                false_negative += 1
            if rule_id in expected_set and rule_id in visible_set:
                visible += 1
            if rule_id in github_ready_set:
                github_ready += 1

        detected_total = true_positive + false_positive
        metrics[rule_id] = {
            "expected": expected,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "visible": visible,
            "github_ready": github_ready,
            "precision": round(true_positive / detected_total, 4) if detected_total else 1.0,
            "recall": round(true_positive / expected, 4) if expected else 1.0,
        }

    return metrics


def _rule_ids_from_rule_findings(rule_findings: Dict[str, List[RuleFinding]]) -> Set[str]:
    return {
        finding.rule_id
        for findings in rule_findings.values()
        for finding in findings
    }


def _file(path: str, patch: str, raw_content: str = "") -> ChangedFile:
    additions = sum(1 for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in patch.splitlines() if line.startswith("-") and not line.startswith("---"))
    return ChangedFile(
        file_path=path,
        change_type="modified",
        additions=additions,
        deletions=deletions,
        patch=patch,
        raw_content=raw_content,
    )


def _test_file(path: str) -> ChangedFile:
    return _file(path, """@@ -1,2 +1,4 @@
+def test_changed_behavior():
+    assert True
""")
