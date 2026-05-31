import re
import json
from typing import Iterable

from sqlalchemy.orm.attributes import set_committed_value

from app.rule_catalog import get_rule_suggestion


STATIC_RULE_ID_PATTERN = re.compile(r"^S\d{3}$")


def hydrate_missing_suggestions(findings: Iterable[object]) -> None:
    """Fill missing static-rule display fields for legacy persisted findings."""
    for finding in findings:
        finding_type = getattr(finding, "finding_type", None)
        if not finding_type or not STATIC_RULE_ID_PATTERN.match(str(finding_type)):
            continue

        suggestion = getattr(finding, "suggestion", None)
        if not suggestion or not suggestion.strip():
            hydrated_suggestion = get_rule_suggestion(str(finding_type))
            _set_display_value(finding, "suggestion", hydrated_suggestion)

        _hydrate_review_source(finding, str(finding_type))


def _hydrate_review_source(finding: object, rule_id: str) -> None:
    raw_evidence = getattr(finding, "evidence_json", None)
    try:
        evidence = json.loads(raw_evidence) if raw_evidence else []
    except (TypeError, json.JSONDecodeError):
        evidence = []

    if not isinstance(evidence, list):
        evidence = []

    if any(isinstance(item, dict) and item.get("type") == "review_source" for item in evidence):
        return

    evidence.insert(0, {
        "type": "review_source",
        "label": "Review Source",
        "content": f"Static Rule {rule_id}",
    })
    _set_display_value(finding, "evidence_json", json.dumps(evidence, ensure_ascii=False))


def _set_display_value(finding: object, field_name: str, value: str) -> None:
    try:
        set_committed_value(finding, field_name, value)
    except Exception:
        setattr(finding, field_name, value)
