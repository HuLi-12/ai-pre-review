"""Golden evaluation cases for the PR review engine.

The cases are intentionally local and deterministic so judging/demo runs can
measure review quality without depending on GitHub or an LLM provider.
"""

from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict

from app.github_client import ChangedFile, GitHubClient
from app.review_engine import ReviewEngine
from app.static_scanner import RuleFinding, StaticScanner
from app.confidence_calculator import should_comment_to_github


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    title: str
    changed_files: List[ChangedFile]
    expected_rule_ids: Set[str]
    source_url: str = ""
    source_label: str = ""


@dataclass
class GoldenCaseResult:
    case_id: str
    title: str
    source_url: str
    source_label: str
    expected_rule_ids: List[str]
    detected_rule_ids: List[str]
    visible_rule_ids: List[str]
    github_ready_rule_ids: List[str]
    missing_rule_ids: List[str]
    unexpected_rule_ids: List[str]
    baseline_candidate_count: int = 0
    raw_finding_count: int = 0
    invalid_finding_count: int = 0
    deduped_finding_count: int = 0
    visible_finding_count: int = 0
    evidence_backed_count: int = 0
    evidence_gate_retention_rate: float = 1.0
    finding_evidence: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class GoldenEvaluationReport:
    total_cases: int
    expected_total: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    visible_expected_count: int
    github_ready_count: int
    baseline_candidate_count: int
    raw_finding_count: int
    invalid_finding_count: int
    deduped_finding_count: int
    visible_finding_count: int
    evidence_backed_count: int
    noise_filtered_count: int
    evidence_gate_retention_rate: float
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


def get_real_pr_replay_cases() -> List[GoldenCase]:
    """Fixed public PR diff snapshots used for repeatable replay evaluation.

    The snapshots are intentionally stored locally so demo/evaluation runs do
    not depend on GitHub availability or on a PR changing over time.
    """
    return [
        GoldenCase(
            case_id="real_localtunnel_auth_pr",
            title="localtunnel adds CLI authentication options without tests",
            changed_files=_files_from_diff("""diff --git a/README.md b/README.md
index 418531dc..1f64e87e 100644
--- a/README.md
+++ b/README.md
@@ -42,6 +42,8 @@ Below are some common arguments. See `lt --help` for additional arguments
 - `--subdomain` request a named subdomain on the localtunnel server (default is random characters)
 - `--local-host` proxy to a hostname other than localhost
+- `--username` username for basic authentication
+- `--password` password for basic authentication
diff --git a/bin/lt.js b/bin/lt.js
index 1e2110a2..49976327 100755
--- a/bin/lt.js
+++ b/bin/lt.js
@@ -42,6 +42,14 @@ const { argv } = yargs
   .option('allow-invalid-cert', {
     describe: 'Disable certificate checks for your local HTTPS server (ignore cert/key/ca options)',
   })
+  .option('u', {
+    alias: 'username',
+    describe: 'Username for basic authentication',
+  })
+  .option('w', {
+    alias: 'password',
+    describe: 'Password for basic authentication',
+  })
@@ -63,7 +71,16 @@ if (typeof argv.port !== 'number') {
 }
 
 (async () => {
-  const tunnel = await localtunnel({
+  const opts = {
     port: argv.port,
     host: argv.host,
     subdomain: argv.subdomain,
@@ -73,7 +90,7 @@ if (typeof argv.port !== 'number') {
     local_key: argv.localKey,
     local_ca: argv.localCa,
     allow_invalid_cert: argv.allowInvalidCert,
-  }).catch(err => {
+  };
diff --git a/lib/Tunnel.js b/lib/Tunnel.js
index 17399c9c..a0f93305 100644
--- a/lib/Tunnel.js
+++ b/lib/Tunnel.js
@@ -51,6 +51,8 @@ module.exports = class Tunnel extends EventEmitter {
       responseType: 'json',
     };
 
+    if(opt.auth) params.auth = opt.auth;
+
     const baseUri = `${opt.host}/`;
"""),
            expected_rule_ids={"S015"},
            source_url="https://github.com/localtunnel/localtunnel/pull/339",
            source_label="localtunnel/localtunnel#339",
        ),
        GoldenCase(
            case_id="real_flask_dependency_bump",
            title="Flask dependency-only update should stay clean",
            changed_files=_files_from_diff("""diff --git a/requirements/build.txt b/requirements/build.txt
index 6bfd666c59..0009cb0cbc 100644
--- a/requirements/build.txt
+++ b/requirements/build.txt
@@ -4,7 +4,7 @@
 #
 #    pip-compile build.in
 #
-build==1.0.3
+build==1.1.1
     # via -r build.in
diff --git a/requirements/tests.txt b/requirements/tests.txt
index 7fdb2d0372..0428c5fd3b 100644
--- a/requirements/tests.txt
+++ b/requirements/tests.txt
@@ -12,7 +12,7 @@ packaging==23.2
 pluggy==1.3.0
     # via pytest
-pytest==8.0.0
+pytest==8.0.2
     # via -r tests.in
"""),
            expected_rule_ids=set(),
            source_url="https://github.com/pallets/flask/pull/5425",
            source_label="pallets/flask#5425",
        ),
        GoldenCase(
            case_id="real_requests_test_only",
            title="Requests test-only URL validation change should stay clean",
            changed_files=_files_from_diff("""diff --git a/tests/test_requests.py b/tests/test_requests.py
index d05febeef5..b4e9fe92ae 100644
--- a/tests/test_requests.py
+++ b/tests/test_requests.py
@@ -2721,7 +2721,7 @@ def test_preparing_bad_url(self, url):
         with pytest.raises(requests.exceptions.InvalidURL):
             r.prepare()
 
-    @pytest.mark.parametrize("url, exception", (("http://localhost:-1", InvalidURL),))
+    @pytest.mark.parametrize("url, exception", (("http://:1", InvalidURL),))
     def test_redirecting_to_bad_url(self, httpbin, url, exception):
         with pytest.raises(exception):
             requests.get(httpbin("redirect-to"), params={"url": url})
"""),
            expected_rule_ids=set(),
            source_url="https://github.com/psf/requests/pull/6700",
            source_label="psf/requests#6700",
        ),
        GoldenCase(
            case_id="real_fastapi_docs_typo",
            title="FastAPI documentation-only typo fix should stay clean",
            changed_files=_files_from_diff("""diff --git a/docs/es/docs/async.md b/docs/es/docs/async.md
index 0fdc307391b5b..dcd6154be41e9 100644
--- a/docs/es/docs/async.md
+++ b/docs/es/docs/async.md
@@ -190,7 +190,7 @@ Luego, el cajero / cocinero finalmente regresa con tus hamburguesas
 
 <img src="https://fastapi.tiangolo.com/img/async/parallel-burgers/parallel-burgers-05.png" alt="illustration">
 
-Cojes tus hamburguesas y vas a la mesa con esa persona.
+Coges tus hamburguesas y vas a la mesa con esa persona.
 
 Solo las comes y listo.
"""),
            expected_rule_ids=set(),
            source_url="https://github.com/fastapi/fastapi/pull/11400",
            source_label="fastapi/fastapi#11400",
        ),
        GoldenCase(
            case_id="real_click_source_with_tests",
            title="Click source change with matching tests should not trigger test-gap noise",
            changed_files=_files_from_diff("""diff --git a/src/click/core.py b/src/click/core.py
index c8d94ab..f6b5a2d 100644
--- a/src/click/core.py
+++ b/src/click/core.py
@@ -742,6 +742,8 @@ class Context:
         if default_map is None:
             default_map = {}
+        if resilient_parsing:
+            default_map = default_map.copy()
         self.default_map = default_map
diff --git a/tests/test_defaults.py b/tests/test_defaults.py
index 9728c10..2a89c61 100644
--- a/tests/test_defaults.py
+++ b/tests/test_defaults.py
@@ -88,6 +88,9 @@ def test_default_map(runner):
     assert result.exit_code == 0
+def test_default_map_resilient_parsing(runner):
+    assert runner is not None
"""),
            expected_rule_ids=set(),
            source_url="https://github.com/pallets/click/pull/2730",
            source_label="pallets/click#2730",
        ),
    ]


def run_real_pr_replay_evaluation() -> GoldenEvaluationReport:
    return run_golden_evaluation(get_real_pr_replay_cases())


def run_golden_evaluation(cases: Optional[List[GoldenCase]] = None) -> GoldenEvaluationReport:
    selected_cases = cases or get_golden_cases()
    case_results = [_evaluate_case(case) for case in selected_cases]

    expected_total = sum(len(case.expected_rule_ids) for case in selected_cases)
    true_positive_count = sum(len(result.expected_detected_rule_ids) for result in _internal_results(case_results))
    false_positive_count = sum(len(result.unexpected_rule_ids) for result in case_results)
    false_negative_count = sum(len(result.missing_rule_ids) for result in case_results)
    visible_expected_count = sum(len(result.expected_visible_rule_ids) for result in _internal_results(case_results))
    github_ready_count = sum(len(result.github_ready_rule_ids) for result in case_results)
    baseline_candidate_count = sum(result.baseline_candidate_count for result in case_results)
    raw_finding_count = sum(result.raw_finding_count for result in case_results)
    invalid_finding_count = sum(result.invalid_finding_count for result in case_results)
    deduped_finding_count = sum(result.deduped_finding_count for result in case_results)
    visible_finding_count = sum(result.visible_finding_count for result in case_results)
    evidence_backed_count = sum(result.evidence_backed_count for result in case_results)
    noise_filtered_count = max(0, baseline_candidate_count - visible_finding_count)
    evidence_gate_retention_rate = round(
        visible_finding_count / baseline_candidate_count, 4
    ) if baseline_candidate_count else 1.0

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
        baseline_candidate_count=baseline_candidate_count,
        raw_finding_count=raw_finding_count,
        invalid_finding_count=invalid_finding_count,
        deduped_finding_count=deduped_finding_count,
        visible_finding_count=visible_finding_count,
        evidence_backed_count=evidence_backed_count,
        noise_filtered_count=noise_filtered_count,
        evidence_gate_retention_rate=evidence_gate_retention_rate,
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
    counts = getattr(engine, "_pipeline_counts", {})

    detected = _rule_ids_from_rule_findings(rule_findings)
    visible = {finding.get("type", "") for finding in merged}
    github_ready = {
        finding.get("type", "")
        for finding in merged
        if should_comment_to_github(finding.get("confidence", 0) or 0, finding.get("severity", "low"))
    }

    missing = case.expected_rule_ids - detected
    unexpected = detected - case.expected_rule_ids
    baseline_candidate_count = counts.get("raw", len(merged))
    visible_finding_count = counts.get("visible", len(merged))
    evidence_backed_count = sum(1 for finding in merged if _has_evidence_backing(finding))

    return GoldenCaseResult(
        case_id=case.case_id,
        title=case.title,
        source_url=case.source_url,
        source_label=case.source_label,
        expected_rule_ids=sorted(case.expected_rule_ids),
        detected_rule_ids=sorted(detected),
        visible_rule_ids=sorted(visible),
        github_ready_rule_ids=sorted(github_ready),
        missing_rule_ids=sorted(missing),
        unexpected_rule_ids=sorted(unexpected),
        baseline_candidate_count=baseline_candidate_count,
        raw_finding_count=counts.get("raw", len(merged)),
        invalid_finding_count=counts.get("invalid", 0),
        deduped_finding_count=counts.get("deduped", len(merged)),
        visible_finding_count=visible_finding_count,
        evidence_backed_count=evidence_backed_count,
        evidence_gate_retention_rate=round(
            visible_finding_count / baseline_candidate_count, 4
        ) if baseline_candidate_count else 1.0,
        finding_evidence=_build_case_evidence(rule_findings, merged),
    )


def _has_evidence_backing(finding: dict) -> bool:
    return bool(
        finding.get("line_content")
        or finding.get("confidence_reason")
        or finding.get("source") == "static_rule"
        or finding.get("changed_line_evidence")
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


def _build_case_evidence(
    rule_findings: Dict[str, List[RuleFinding]],
    merged_findings: List[dict],
) -> List[Dict[str, object]]:
    confidence_by_rule = {
        finding.get("type", ""): finding.get("confidence", 0) or 0
        for finding in merged_findings
    }
    severity_by_rule = {
        finding.get("type", ""): finding.get("severity", "low")
        for finding in merged_findings
    }
    confidence_reason_by_rule = {
        finding.get("type", ""): finding.get("confidence_reason", "")
        for finding in merged_findings
    }

    evidence = []
    for file_path, findings in rule_findings.items():
        for finding in findings:
            confidence = confidence_by_rule.get(finding.rule_id, 0)
            severity = severity_by_rule.get(finding.rule_id, finding.severity)
            github_ready = should_comment_to_github(confidence, severity)
            evidence.append({
                "rule_id": finding.rule_id,
                "file_path": finding.file_path or file_path,
                "line_number": finding.line_number,
                "line_content": finding.line_content,
                "source": "static_rule",
                "confidence": confidence,
                "confidence_reason": confidence_reason_by_rule.get(
                    finding.rule_id,
                    "Static rule matched changed-line evidence",
                ),
                "gate": "github_ready" if github_ready else "visible" if confidence >= 0.60 else "hidden",
                "message": finding.message,
            })
    return evidence


def _files_from_diff(diff_text: str) -> List[ChangedFile]:
    return GitHubClient._parse_unified_diff_files(diff_text)


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
