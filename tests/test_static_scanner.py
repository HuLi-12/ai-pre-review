"""Tests for static_scanner.py — patch-only rule scanning."""

from app.static_scanner import StaticScanner


def test_s005_hardcoded_password_detected():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,5 @@
 def auth():
+    password = "secret123"
     return ok
"""
    findings = scanner.scan_patch("test.py", patch)
    s005 = [f for f in findings if f.rule_id == "S005"]
    assert len(s005) == 1
    assert s005[0].severity == "critical"


def test_s014_unsafe_delete_detected():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,5 @@
 def clean():
+    DELETE FROM users
     return
"""
    findings = scanner.scan_patch("test.py", patch)
    s014 = [f for f in findings if f.rule_id == "S014"]
    assert len(s014) == 1
    assert s014[0].severity == "critical"


def test_s014_delete_with_where_is_safe():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,5 @@
 def clean():
+    db.delete("users WHERE id = 1")
     return
"""
    findings = scanner.scan_patch("test.py", patch)
    s014 = [f for f in findings if f.rule_id == "S014"]
    assert len(s014) == 0


def test_s011_loop_db_call_detected():
    scanner = StaticScanner()
    patch = """@@ -1,5 +1,10 @@
 def process(items):
+    for item in items:
+        user = db.query(User).filter(User.id == item).first()
+        users.append(user)
     return users
"""
    findings = scanner.scan_patch("test.py", patch)
    s011 = [f for f in findings if f.rule_id == "S011"]
    assert len(s011) == 1


def test_s010_broad_exception_detected():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,7 @@
 def risky():
+    try {
+        do_something();
+    } catch (Exception e) {
+    }
"""
    findings = scanner.scan_patch("test.py", patch)
    s010 = [f for f in findings if f.rule_id == "S010"]
    assert len(s010) >= 1


def test_s008_fastapi_endpoint_detected():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,6 @@
 router = APIRouter()
+@router.post("/admin/delete")
+def delete_user(user_id: int):
+    return service.delete_user(user_id)
"""
    findings = scanner.scan_patch("routes.py", patch)
    s008 = [f for f in findings if f.rule_id == "S008"]
    assert len(s008) == 1
    assert s008[0].severity == "high"


def test_s009_fastapi_endpoint_without_validation_detected():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,6 @@
 router = APIRouter()
+@app.post("/users")
+def create_user(name: str):
+    return service.create_user(name)
"""
    findings = scanner.scan_patch("main.py", patch)
    s009 = [f for f in findings if f.rule_id == "S009"]
    assert len(s009) == 1
    assert s009[0].severity == "medium"


def test_static_scanner_skips_documentation_code_examples():
    scanner = StaticScanner()
    patch = """@@ -1,3 +1,8 @@
+```python
+@app.post("/users")
+def create_user(name: str):
+    return {"name": name}
+```
"""
    findings = scanner.scan_patch("docs/advanced.md", patch)
    assert findings == []


def test_unchanged_old_code_not_scanned():
    """Patch-only scanning MUST NOT flag issues in unchanged lines."""
    scanner = StaticScanner()
    # Only line 3 (context) is unchanged — scanner should only check added lines
    patch = """@@ -1,5 +1,6 @@
 # old code with print
 # old code with TODO
+    new_line_only()
     return
"""
    findings = scanner.scan_patch("test.py", patch)
    s001 = [f for f in findings if f.rule_id == "S001"]
    s002 = [f for f in findings if f.rule_id == "S002"]
    assert len(s001) == 0, "Should not flag print in unchanged old code"
    assert len(s002) == 0, "Should not flag TODO in unchanged old code"


def test_scan_patch_empty():
    scanner = StaticScanner()
    assert scanner.scan_patch("test.py", "") == []
    assert scanner.scan_patch("test.py", None) == []
