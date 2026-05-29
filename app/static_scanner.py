import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class RuleFinding:
    file_path: str
    line_number: int
    rule_id: str
    severity: str  # high / medium / low
    message: str
    line_content: str = ""


class StaticScanner:
    """Static rule scanning engine.
    Handles deterministic code issues that don't require semantic understanding.
    """

    def __init__(self):
        self.rules = [
            _Rule("S001", "hardcoded_print", "high",
                  "Hardcoded print statement detected (System.out / print)",
                  [r'\bSystem\.out\.(print|println|printf)',
                   r'\bprint\s*\(',
                   r'\bconsole\.log\b',
                   r'\bconsole\.info\b']),
            _Rule("S002", "todo_fixme", "low",
                  "TODO or FIXME comment left in code",
                  [r'#\s*TODO', r'#\s*FIXME',
                   r'//\s*TODO', r'//\s*FIXME',
                   r'/\*\s*TODO', r'/\*\s*FIXME']),
            _Rule("S003", "empty_catch", "high",
                  "Empty catch block detected — exception is swallowed",
                  [r'catch\s*\(.*\)\s*\{\s*\}']),
            _Rule("S004", "sensitive_log", "high",
                  "Potential sensitive info in log (password/secret/token)",
                  [r'log(?:ger)?\.\w+\s*\(.*password',
                   r'log(?:ger)?\.\w+\s*\(.*secret',
                   r'log(?:ger)?\.\w+\s*\(.*token',
                   r'log(?:ger)?\.\w+\s*\(.*credential']),
            _Rule("S005", "hardcoded_password", "critical",
                  "Hardcoded password or secret detected",
                  [r'password\s*=\s*["\'][^"\']+["\']',
                   r'secret\s*=\s*["\'][^"\']+["\']',
                   r'api_key\s*=\s*["\'][^"\']+["\']',
                   r'apiKey\s*=\s*["\'][^"\']+["\']']),
            _Rule("S006", "missing_null_check", "medium",
                  "Potential null pointer risk — method call without null check",
                  [r'(?:var|let|const)\s+\w+\s*=\s*\w+\.\w+\(.*\)']),
            _Rule("S007", "large_method", "medium",
                  "Method is very large — consider refactoring",
                  []),  # Special case, handled by line counting
        ]

    def scan_file(self, file_path: str, content: str) -> List[RuleFinding]:
        """Scan a single file and return rule findings"""
        findings = []
        if not content:
            return findings

        lines = content.split("\n")

        for rule in self.rules:
            if rule.rule_id == "S007":
                self._check_method_length(file_path, lines, findings)
                continue

            for pattern in rule.patterns:
                for i, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        findings.append(RuleFinding(
                            file_path=file_path,
                            line_number=i,
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=rule.message,
                            line_content=line.strip(),
                        ))

        return findings

    def _check_method_length(self, file_path: str, lines: list, findings: List[RuleFinding]):
        """Check if methods are too long (over 80 lines)"""
        in_method = False
        method_start = 0
        brace_count = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'(def |public |private |protected ).*\(', stripped):
                in_method = True
                method_start = i
                brace_count = 0
                continue

            if in_method:
                brace_count += stripped.count("{") - stripped.count("}")
                if brace_count <= 0 and "{" in stripped:
                    method_length = i - method_start
                    if method_length > 80:
                        findings.append(RuleFinding(
                            file_path=file_path,
                            line_number=method_start,
                            rule_id="S007",
                            severity="medium",
                            message=f"Method starting at line {method_start} has {method_length} lines, consider refactoring",
                        ))
                    in_method = False


class _Rule:
    def __init__(self, rule_id: str, name: str, severity: str, message: str, patterns: List[str]):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.message = message
        self.patterns = patterns
