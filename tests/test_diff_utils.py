"""Tests for diff_utils.py — patch line number parsing."""

from app.diff_utils import parse_patch, get_added_line_numbers, summarize_patch_stats


def test_parse_basic_patch():
    patch = """@@ -1,4 +1,5 @@
 def foo():
+    print("hello")
     x = 1
-    return x
+    return x + 1
 """
    lines = parse_patch(patch)
    assert len(lines) == 2
    assert lines[0]["new_line"] == 2
    assert "print" in lines[0]["content"]
    assert lines[1]["new_line"] == 4
    assert "return" in lines[1]["content"]


def test_parse_empty_patch():
    assert parse_patch("") == []
    assert parse_patch(None) == []


def test_get_added_line_numbers():
    patch = """@@ -1,3 +1,6 @@
 a
+b
 c
+d
+e
 f
"""
    numbers = get_added_line_numbers(patch)
    assert numbers == [2, 4, 5]


def test_patch_with_multiple_hunks():
    patch = """@@ -1,3 +1,4 @@
 a
+b
 c
@@ -10,5 +11,7 @@
 d
+e
 f
+g
 h
"""
    lines = parse_patch(patch)
    assert len(lines) == 3
    assert lines[0]["new_line"] == 2
    assert lines[1]["new_line"] == 12  # 11 + 1 offset
    assert lines[2]["new_line"] == 14


def test_patch_stats():
    patch = """@@ -1,1 +1,3 @@
+a
+b
"""
    stats = summarize_patch_stats(patch)
    assert stats["total_added"] == 2
    assert len(stats["lines"]) == 2
