import re
from typing import List, Optional, Dict
from dataclasses import dataclass

from app.diff_utils import parse_patch

API_ENDPOINT_PATTERN = (
    r'@(?:Post|Get|Put|Delete|Patch|RequestMapping)\b|'
    r'@\s*(?:app|router|api|[\w_]*router)\.(?:get|post|put|delete|patch|route)\s*\('
)
DOCUMENTATION_EXTENSIONS = (".md", ".markdown", ".rst", ".txt", ".adoc")


@dataclass
class RuleFinding:
    file_path: str
    line_number: int
    rule_id: str
    severity: str  # critical / high / medium / low
    message: str
    line_content: str = ""


class StaticScanner:
    """Static rule scanning engine.
    Scans only added/modified lines from patch to avoid false positives on existing code.
    """

    def __init__(self):
        self.rules = [
            # S001: Hardcoded print
            _Rule("S001", "hardcoded_print", "high",
                  "Hardcoded print/debug statement detected",
                  [r'\bSystem\.out\.(print|println|printf)',
                   r'\bprint\s*\(',
                   r'\bconsole\.log\b',
                   r'\bconsole\.info\b',
                   r'\bconsole\.warn\b',
                   r'\bconsole\.error\b']),
            # S002: TODO/FIXME
            _Rule("S002", "todo_fixme", "low",
                  "TODO or FIXME comment left in code",
                  [r'#\s*TODO', r'#\s*FIXME',
                   r'//\s*TODO', r'//\s*FIXME',
                   r'/\*\s*TODO', r'/\*\s*FIXME']),
            # S003: Empty catch
            _Rule("S003", "empty_catch", "high",
                  "Empty catch block — exception is swallowed",
                  [r'catch\s*\(.*\)\s*\{\s*\}']),
            # S004: Sensitive info in log
            _Rule("S004", "sensitive_log", "high",
                  "Potential sensitive info in log (password/secret/token)",
                  [r'log(?:ger)?\.\w+\s*\(.*password',
                   r'log(?:ger)?\.\w+\s*\(.*secret',
                   r'log(?:ger)?\.\w+\s*\(.*token',
                   r'log(?:ger)?\.\w+\s*\(.*credential',
                   r'log(?:ger)?\.\w+\s*\(.*api.?key']),
            # S005: Hardcoded password/secret
            _Rule("S005", "hardcoded_password", "critical",
                  "Hardcoded password or secret detected",
                  [r'password\s*=\s*["\'][^"\']+["\']',
                   r'secret\s*=\s*["\'][^"\']+["\']',
                   r'api_key\s*=\s*["\'][^"\']+["\']',
                   r'apiKey\s*=\s*["\'][^"\']+["\']']),
            # S006: Missing null check (simplified)
            _Rule("S006", "missing_null_check", "medium",
                  "Method call result without null check",
                  []),  # Handled via AI, pattern too broad for static
            # S007: Large method
            _Rule("S007", "large_method", "medium",
                  "Method is very large — consider refactoring",
                  []),  # Special case
            # S008: Missing auth check on new API
            _Rule("S008", "missing_auth_check", "high",
                  "New API method may be missing authentication/authorization",
                  [API_ENDPOINT_PATTERN]),
            # S009: Missing parameter validation
            _Rule("S009", "missing_validation", "medium",
                  "New API endpoint missing parameter validation",
                  []),  # Handled via AI + pattern combination
            # S010: Broad exception catch
            _Rule("S010", "broad_exception", "high",
                  "Catching overly broad Exception/Throwable",
                  [r'catch\s*\(\s*(?:Exception|Throwable)\s', r'catch\s*\(.*Exception\s+']),
            # S011: Loop database call
            _Rule("S011", "loop_db_call", "high",
                  "Database/API call inside a loop — potential N+1 problem",
                  [r'for\s+.*:', r'for\s*\(', r'while\s*\(',
                   r'\.forEach\s*\(']),
            # S012: No pagination on list query
            _Rule("S012", "no_pagination_query", "medium",
                  "List query without obvious pagination or limit",
                  []),  # Handled via AI
            # S013: Transaction risk on multi-write
            _Rule("S013", "transaction_risk", "high",
                  "Multiple database writes within a method without transaction",
                  []),  # Handled via AI
            # S014: Unsafe delete/update without where
            _Rule("S014", "unsafe_delete_or_update", "critical",
                  "Delete/update operation without visible WHERE condition",
                  [r'\bdelete\s+from\b', r'\bdelete\b.*\bwhere\b',
                   r'\bupdate\b.*\bset\b', r'\bupdate\b.*\bwhere\b']),
            # S015: Test missing for core change
            _Rule("S015", "test_missing_for_core_change", "medium",
                  "Core source file changed but test file not updated",
                  []),  # Handled via cross-file analysis
        ]

    def scan_patch(self, file_path: str, patch: str, full_content: str = "") -> List[RuleFinding]:
        """Scan only the added lines in a patch for rule violations.

        This is the primary entry point — it only flags issues in NEW code.
        """
        if file_path.lower().endswith(DOCUMENTATION_EXTENSIONS):
            return []

        findings = []
        if not patch:
            return findings

        added_lines = parse_patch(patch)
        if not added_lines:
            return findings

        for rule in self.rules:
            if rule.rule_id == "S007":
                # Large method: only flag if the method was modified in this PR
                self._check_method_length_on_patch(file_path, full_content, patch, findings)
                continue
            if rule.rule_id == "S006":
                continue  # Skip S006 for static, handled by AI
            if rule.rule_id == "S009":
                self._check_missing_validation(file_path, added_lines, findings)
                continue
            if rule.rule_id == "S011":
                # Loop DB call: check if loop and db call are both added
                self._check_loop_db_call(file_path, added_lines, findings)
                continue
            if rule.rule_id == "S013":
                continue  # Transaction risk handled by AI
            if rule.rule_id == "S015":
                continue  # Test coverage handled by cross-file analysis

            # Standard pattern matching on added lines only
            for item in added_lines:
                line_text = item["content"]
                for pattern in rule.patterns:
                    if re.search(pattern, line_text, re.IGNORECASE):
                        # For S014, check if the pattern indicates unsafe operation
                        if rule.rule_id == "S014":
                            if self._is_safe_sql(item["content"]):
                                continue

                        findings.append(RuleFinding(
                            file_path=file_path,
                            line_number=item["new_line"],
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=rule.message,
                            line_content=line_text.strip(),
                        ))
                        break  # One finding per line per rule

        return findings

    def scan_file(self, file_path: str, content: str) -> List[RuleFinding]:
        """Legacy: scan full file content. Kept for backwards compatibility."""
        return self.scan_patch(file_path, content)

    def _is_safe_sql(self, line: str) -> bool:
        """Heuristic: check if a SQL statement has a WHERE clause."""
        line_lower = line.strip().lower()
        if "delete" in line_lower or "update" in line_lower:
            if "where" in line_lower:
                return True
            if line_lower.count("delete") > 1 or line_lower.count("update") > 1:
                return False
        return False

    def _check_loop_db_call(self, file_path: str, added_lines: list, findings: List[RuleFinding]):
        """Check if a loop is added that contains db/api calls inside."""
        loop_lines = []
        for item in added_lines:
            line = item["content"]
            if re.search(r'(for\s+.*:|for\s*\(|while\s*\(|\.forEach\s*\()', line):
                loop_lines.append(item)

        for loop_item in loop_lines:
            # Look for database keywords within 3 lines after the loop
            loop_line = loop_item["new_line"]
            for other in added_lines:
                if 0 < other["new_line"] - loop_line <= 3:
                    db_keywords = ['mapper', 'repository', '.save(', '.find', '.query',
                                   '.update(', '.delete(', '.get(', '.all(',
                                   'db.', 'session.', 'cursor.', 'execute(']
                    for kw in db_keywords:
                        if kw in other["content"].lower():
                            findings.append(RuleFinding(
                                file_path=file_path,
                                line_number=other["new_line"],
                                rule_id="S011",
                                severity="high",
                                message="Database/API call inside a loop — potential N+1 query problem",
                                line_content=other["content"].strip(),
                            ))
                            break

    def _check_missing_validation(self, file_path: str, added_lines: list, findings: List[RuleFinding]):
        """Check if a new API endpoint has parameter validation."""
        has_new_api = False
        api_line = 0

        for item in added_lines:
            if re.search(API_ENDPOINT_PATTERN, item["content"], re.IGNORECASE):
                has_new_api = True
                api_line = item["new_line"]
                break

        if not has_new_api:
            return

        # Look for @Valid or validation annotations in nearby added lines
        has_validation = False
        for item in added_lines:
            if abs(item["new_line"] - api_line) <= 10:
                if re.search(r'@Valid|@Validate|@NotBlank|@NotNull|@NotEmpty|@Size|@Pattern',
                             item["content"]):
                    has_validation = True
                    break

        if not has_validation:
            findings.append(RuleFinding(
                file_path=file_path,
                line_number=api_line,
                rule_id="S009",
                severity="medium",
                message="New API endpoint may be missing parameter validation",
                line_content=added_lines[[x["new_line"] for x in added_lines].index(api_line)]["content"]
                    if api_line in [x["new_line"] for x in added_lines] else "",
            ))

    def _check_method_length_on_patch(self, file_path: str, full_content: str,
                                       patch: str, findings: List[RuleFinding]):
        """Check method length, but only flag if the patch modifies that method."""
        if not full_content or not patch:
            return

        # Parse patch to get affected line ranges
        patch_ranges = self._get_patch_line_ranges(patch)

        # Find methods in full content
        method_starts = []
        lines = full_content.split("\n")
        in_method = False
        method_start = 0
        brace_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'(def |public |private |protected ).*\(', stripped):
                if not in_method:
                    method_starts.append({"line": i, "name": stripped[:60]})
                continue

        # For each large method that appears in the patch, flag it
        for item in method_starts:
            method_end = self._find_method_end(lines, item["line"])
            method_length = method_end - item["line"]
            if method_length > 80:
                # Check if patch touches this method's range
                for r_start, r_end in patch_ranges:
                    if not (r_end < item["line"] or r_start > method_end):
                        findings.append(RuleFinding(
                            file_path=file_path,
                            line_number=item["line"],
                            rule_id="S007",
                            severity="medium",
                            message=f"Modified method at line {item['line']} has {method_length} lines, consider refactoring",
                            line_content=item["name"],
                        ))
                        break

    def _find_method_end(self, lines: list, start: int) -> int:
        """Find end line of a method by brace counting."""
        brace_count = 0
        started = False
        for i in range(start - 1, len(lines)):
            line = lines[i]
            stripped = line.strip()
            if "{" in stripped:
                started = True
            if started:
                brace_count += stripped.count("{") - stripped.count("}")
            if started and brace_count <= 0 and i > start:
                return i + 1
        return len(lines)

    def _get_patch_line_ranges(self, patch: str) -> list:
        """Extract line ranges from patch hunks."""
        ranges = []
        for match in re.finditer(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', patch):
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) else 1
            ranges.append((start, start + count))
        return ranges


class _Rule:
    def __init__(self, rule_id: str, name: str, severity: str, message: str, patterns: List[str]):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.message = message
        self.patterns = patterns
