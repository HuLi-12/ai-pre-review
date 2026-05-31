import re
from typing import Iterable

from app.rule_catalog import get_rule_suggestion


STATIC_RULE_ID_PATTERN = re.compile(r"^S\d{3}$")


def hydrate_missing_suggestions(findings: Iterable[object]) -> None:
    """Fill missing static-rule suggestions for legacy persisted findings."""
    for finding in findings:
        suggestion = getattr(finding, "suggestion", None)
        if suggestion and suggestion.strip():
            continue

        finding_type = getattr(finding, "finding_type", None)
        if not finding_type or not STATIC_RULE_ID_PATTERN.match(str(finding_type)):
            continue

        finding.suggestion = get_rule_suggestion(str(finding_type))

