from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Report:
    risk_level: str = "LOW"
    merge_suggestion: str = ""
    markdown_summary: str = ""
    test_suggestions: List[str] = field(default_factory=list)
    key_focus_points: List[str] = field(default_factory=list)
    findings_by_severity: Dict[str, List[dict]] = field(default_factory=dict)


class ReportGenerator:
    """Generate structured review reports from merged findings."""

    COMMENT_MARKER = "<!-- ai-review-cockpit-comment -->"

    def generate(self, summary: dict, findings: List[dict]) -> Report:
        """Generate a complete review report"""
        report = Report()

        # Categorize findings by severity
        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for fd in findings:
            sev = fd.get("severity", "low").lower()
            if sev in by_severity:
                by_severity[sev].append(fd)
            else:
                by_severity["low"].append(fd)

        report.findings_by_severity = by_severity

        # Determine overall risk level
        if by_severity["critical"]:
            report.risk_level = "CRITICAL"
        elif by_severity["high"]:
            report.risk_level = "HIGH"
        elif by_severity["medium"]:
            report.risk_level = "MEDIUM"
        else:
            report.risk_level = "LOW"

        # Merge suggestion
        if report.risk_level in ("CRITICAL", "HIGH"):
            report.merge_suggestion = "建议修复 high 及以上风险后再合并"
        elif report.risk_level == "MEDIUM":
            report.merge_suggestion = "建议 review medium 风险项，确认后合并"
        else:
            report.merge_suggestion = "可安全合并"

        # Extract test suggestions
        report.test_suggestions = [
            fd.get("suggestion", "") for fd in findings
            if fd.get("type") == "test" or "test" in fd.get("title", "").lower()
        ]

        # Extract key focus points
        report.key_focus_points = [
            fd.get("title", "") for fd in findings
            if fd.get("severity") in ("critical", "high")
        ]

        # Generate markdown summary
        report.markdown_summary = self._to_markdown(summary, by_severity)

        return report

    @staticmethod
    def _to_markdown(summary: dict, by_severity: Dict[str, List[dict]]) -> str:
        """Generate GitHub-compatible markdown report"""
        parts = []

        # One-line summary
        one_line = summary.get("one_line_summary", "")
        if one_line:
            parts.append(f"## AI Review 摘要\n{one_line}\n")

        # Module changes
        module_changes = summary.get("module_changes", {})
        if module_changes:
            parts.append("### 变更模块\n")
            for module, changes in module_changes.items():
                parts.append(f"**{module}:**")
                for c in changes[:10]:
                    parts.append(f"- {c}")
                parts.append("")

        # Business impact
        impacts = summary.get("business_impact", [])
        if impacts:
            parts.append("### 业务影响范围\n")
            for imp in impacts[:5]:
                parts.append(f"- {imp}")
            parts.append("")

        # High risk findings
        for severity in ("critical", "high"):
            findings = by_severity.get(severity, [])
            if findings:
                label = "🔴 严重问题" if severity == "critical" else "🟠 高风险问题"
                parts.append(f"### {label}\n")
                for fd in findings[:10]:
                    parts.append(f"**{fd.get('title', '')}**")
                    parts.append(f"- 文件: `{fd.get('file', '')}` | 行号: {fd.get('line', 'N/A')}")
                    parts.append(f"- 严重等级: {fd.get('severity', '')} | 置信度: {fd.get('confidence', 'N/A')}")
                    if fd.get('reason'):
                        parts.append(f"- 原因: {fd['reason']}")
                    if fd.get('suggestion'):
                        parts.append(f"- 建议: {fd['suggestion']}")
                    parts.append("")

        # Medium findings
        medium = by_severity.get("medium", [])
        if medium:
            parts.append(f"### 📋 中等建议\n")
            for fd in medium[:10]:
                parts.append(f"- **{fd.get('title', '')}** (`{fd.get('file', '')}`:{fd.get('line', 'N/A')})")
                if fd.get('suggestion'):
                    parts.append(f"  - 建议: {fd['suggestion']}")
            parts.append("")

        # Low findings summary
        low = by_severity.get("low", [])
        if low:
            parts.append(f"### 💡 代码优化建议\n")
            for fd in low[:10]:
                parts.append(f"- {fd.get('title', '')} (`{fd.get('file', '')}`:{fd.get('line', 'N/A')})")
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def generate_github_comment(report: Report) -> str:
        """Generate a concise GitHub PR comment (github_ready findings only)."""
        parts = [ReportGenerator.COMMENT_MARKER]
        parts.append("## 🤖 AI Review Cockpit\n")

        total = sum(len(v) for v in report.findings_by_severity.values())
        if total == 0:
            parts.append("未发现明显问题。\n")
            return "\n".join(parts)

        # Flatten and filter to github_ready findings
        all_findings = []
        for sev_list in report.findings_by_severity.values():
            all_findings.extend(sev_list)
        github_ready = [f for f in all_findings if f.get("github_ready", False)]

        if not github_ready:
            parts.append(f"本次评审共发现 {total} 个问题，但均未达到 GitHub 评论置信标准。\n")
            parts.append("*完整报告请查看 AI Review Cockpit。*\n")
            return "\n".join(parts)

        parts.append(f"**风险等级:** `{report.risk_level}`")
        parts.append(f"**合并建议:** {report.merge_suggestion}")
        parts.append(f"**共发现:** {total} 个问题（{len(github_ready)} 个达到展示标准）\n")

        # Summary
        if report.key_focus_points:
            parts.append("### 重点关注\n")
            for p in report.key_focus_points[:5]:
                parts.append(f"- {p}")
            parts.append("")

        # High severity issues (github_ready filtered)
        high_confidence = [f for f in github_ready if f.get("severity") in ("critical", "high")]

        if high_confidence:
            parts.append("### 高风险问题\n")
            for i, fd in enumerate(high_confidence[:10], 1):
                file_path = fd.get("file", "")
                line = fd.get("line", "")
                title = fd.get("title", "")
                loc = f"`{file_path}`" + (f":{line}" if line else "")
                rule = fd.get("type", "")
                confidence = fd.get("confidence", 0)
                rule_tag = f" [{rule}]" if rule else ""
                conf_tag = f" (conf: {int(float(confidence)*100)}%)" if confidence else ""
                parts.append(f"{i}. {loc} — {title}{rule_tag}{conf_tag}")
            parts.append("")

        # Evidence summary
        if high_confidence:
            parts.append("### 证据摘要\n")
            for fd in high_confidence[:5]:
                file_path = fd.get("file", "")
                title = fd.get("title", "")
                reason = fd.get("reason", "")
                if reason:
                    parts.append(f"- **{title}** (`{file_path}`): {reason[:120]}")
            parts.append("")

        # Medium/low suggestions that are github_ready
        rest = [f for f in github_ready if f.get("severity") not in ("critical", "high")]
        if rest:
            parts.append("### 改进建议\n")
            for fd in rest[:5]:
                parts.append(f"- `{fd.get('file', '')}` — {fd.get('title', '')}")
            parts.append("")

        parts.append("---")
        parts.append("*完整报告请查看 AI Review Cockpit。*")

        return "\n".join(parts)
