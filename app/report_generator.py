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
            parts.append(f"## AI Review Summary\n{one_line}\n")

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
        """Generate a concise GitHub PR comment"""
        parts = []
        parts.append(f"## 🤖 AI Code Review\n")
        parts.append(f"**风险等级:** {report.risk_level}")
        parts.append(f"**合并建议:** {report.merge_suggestion}\n")

        if report.key_focus_points:
            parts.append("### 重点关注\n")
            for p in report.key_focus_points[:5]:
                parts.append(f"- {p}")
            parts.append("")

        total = sum(len(v) for v in report.findings_by_severity.values())
        parts.append(f"共发现 {total} 个问题。查看完整报告获取详细信息。")

        return "\n".join(parts)
