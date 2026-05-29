"""Utilities for parsing unified diff patches and extracting changed lines."""

import re
from typing import List, Dict


def parse_patch(patch: str) -> List[Dict]:
    """Parse a unified diff patch and extract added/modified lines.

    Returns list of dicts:
        {"new_line": int, "content": str}
    """
    if not patch:
        return []

    added_lines = []
    new_line_num = 0

    for line in patch.split("\n"):
        # Match hunk header: @@ -old_start,old_count +new_start,new_count @@
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk_match:
            new_line_num = int(hunk_match.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append({"new_line": new_line_num, "content": line[1:]})
            new_line_num += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass  # Deleted lines don't increment counter
        elif line.startswith("\\"):  # No newline at end of file
            pass
        else:
            # Context line
            new_line_num += 1

    return added_lines


def get_added_line_numbers(patch: str) -> List[int]:
    """Get line numbers of added lines in the patch."""
    return [item["new_line"] for item in parse_patch(patch)]


def is_line_in_patch(patch: str, target_line: int, context: int = 5) -> bool:
    """Check if a line number is within an added/modified region of the patch."""
    added_lines = parse_patch(patch)
    for item in added_lines:
        if abs(item["new_line"] - target_line) <= context:
            return True
    return False


def summarize_patch_stats(patch: str) -> Dict:
    """Get basic stats about a patch."""
    added = [l for l in parse_patch(patch)]
    return {
        "total_added": len(added),
        "lines": added,
    }
