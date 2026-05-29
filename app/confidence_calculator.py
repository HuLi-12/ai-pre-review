"""Confidence scoring for review findings.

Formula:
    confidence = base_score + evidence_score + agreement_score - uncertainty_penalty

Thresholds:
    >= 0.80: High confidence, suitable for GitHub comment
    0.60-0.79: Medium confidence, show in report only
    < 0.60: Low confidence, hide by default
"""


def calculate_confidence(finding: dict, has_rule_match: bool = False) -> float:
    """Calculate confidence score for a finding.

    Rule-specific overrides:
      - S005 (hardcoded_password): 0.85 — deterministic, high-risk
      - S014 (unsafe_delete_or_update): 0.85 — deterministic, high-risk
      - Other critical rules: 0.75
      - Other high rules: 0.65
    """
    source = finding.get("source", "ai_file")

    # Rule-specific overrides for deterministic high-risk rules
    rule_id = finding.get("type", "")
    severity = finding.get("severity", "")
    if source == "static_rule":
        if rule_id in ("S005", "S014"):
            return 0.85
        elif severity == "critical":
            return 0.75
        elif severity == "high":
            return 0.65

    score = 0.0

    # 1. Base score by source
    source_bases = {
        "ai_file": 0.50,
        "static_rule": 0.45,
        "ai_cross": 0.55,
    }
    score += source_bases.get(source, 0.45)

    # 2. Evidence score
    evidence = 0.0
    if finding.get("file"):
        evidence += 0.05
    line = finding.get("line")
    if line and isinstance(line, int) and line > 0:
        evidence += 0.10
        if line < 99999:
            evidence += 0.05  # Plausible line number
    reason = finding.get("reason", "")
    if len(reason) > 30:
        evidence += 0.10  # Has detailed reason
    suggestion = finding.get("suggestion", "")
    if len(suggestion) > 20:
        evidence += 0.10  # Has actionable suggestion

    score += evidence

    # 3. Agreement score: AI + rule both flag same issue
    if has_rule_match:
        score += 0.20

    # 4. Uncertainty penalty
    penalty = 0.0
    if not line or line == 0:
        penalty += 0.10
    if len(reason) < 20:
        penalty += 0.10
    if finding.get("severity") == "low" and source == "ai_file":
        penalty += 0.10
    if source == "ai_file" and finding.get("type") == "maintainability":
        penalty += 0.05

    score -= penalty

    return max(0.0, min(1.0, score))


def adjust_by_rule_match(ai_finding: dict, rule_finding: dict) -> float:
    """Calculate agreement-adjusted confidence when AI and rule both flag."""
    base = calculate_confidence(ai_finding, has_rule_match=True)
    return base


def should_show_in_report(confidence: float) -> bool:
    """Check if finding should be visible in report."""
    return confidence >= 0.60


def should_comment_to_github(confidence: float, severity: str) -> bool:
    """Check if finding is suitable for GitHub PR comment."""
    if confidence >= 0.80:
        return True
    if severity in ("critical", "high") and confidence >= 0.70:
        return True
    return False
