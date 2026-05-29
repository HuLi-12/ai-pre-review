import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.github_client import GitHubClient, ChangedFile, PRInfo
from app.static_scanner import StaticScanner, RuleFinding
from app.context_builder import ContextBuilder, ReviewContext
from app.ai_client import AIClient
from app.models import PRReviewTask, PRChangedFile, PRReviewFinding
from app.report_generator import ReportGenerator


@dataclass
class ReviewResult:
    summary: dict = field(default_factory=dict)
    file_findings: List[dict] = field(default_factory=list)
    cross_file_findings: List[dict] = field(default_factory=list)
    merged_findings: List[dict] = field(default_factory=list)
    risk_level: str = "LOW"
    merge_suggestion: str = ""
    test_suggestions: List[str] = field(default_factory=list)
    key_focus_points: List[str] = field(default_factory=list)


class ReviewEngine:
    """Multi-stage AI Review orchestration engine."""

    def __init__(self, github_token: Optional[str] = None):
        self.github = GitHubClient(token=github_token)
        self.scanner = StaticScanner()
        self.ai = AIClient()
        self.report_gen = ReportGenerator()

    async def run_review(self, task: PRReviewTask, db: Session) -> ReviewResult:
        """Execute full review pipeline"""
        result = ReviewResult()
        owner, repo, number = task.repo_owner, task.repo_name, task.pr_number

        try:
            # ---- Stage 1: PR Understanding ----
            await self._update_progress(task, db, "FETCHING_PR", 10)
            pr_info = self.github.get_pr_info(owner, repo, number)
            changed_files = self.github.get_changed_files(owner, repo, number)
            task.commit_sha = pr_info.commit_sha

            # Save changed files to DB
            self._save_changed_files(task.id, changed_files, db)

            # ---- Stage 2: Build Context ----
            await self._update_progress(task, db, "BUILDING_CONTEXT", 20)
            context_builder = ContextBuilder(self.github, owner, repo, ref=pr_info.source_branch or "main")
            review_context = context_builder.build(changed_files)

            # ---- Stage 3: Static Rule Scanning ----
            await self._update_progress(task, db, "STATIC_SCAN", 30)
            rule_findings = self._run_static_scan(changed_files)

            # ---- Stage 4: AI Review (phased) ----
            # Phase 4.1: PR Summary
            await self._update_progress(task, db, "AI_PR_SUMMARY", 40)
            summary = await self._summarize_pr(pr_info, changed_files)

            # Phase 4.2: File-level analysis
            await self._update_progress(task, db, "AI_FILE_REVIEW", 55)
            file_findings = await self._review_files(changed_files, review_context, rule_findings)

            # Phase 4.3: Cross-file analysis
            await self._update_progress(task, db, "AI_CROSS_FILE", 70)
            cross_findings = await self._cross_file_analysis(changed_files, review_context, file_findings)

            # ---- Stage 5: Merge & Dedup ----
            await self._update_progress(task, db, "MERGING_RESULTS", 85)
            merged = self._merge_findings(file_findings, cross_findings, rule_findings)

            # ---- Stage 6: Generate Report ----
            await self._update_progress(task, db, "GENERATING_REPORT", 95)
            report = self.report_gen.generate(summary, merged)

            # Save findings to DB
            self._save_findings(task.id, merged, db)

            # Update task
            result.summary = summary
            result.file_findings = file_findings
            result.cross_file_findings = cross_findings
            result.merged_findings = merged
            result.risk_level = report.risk_level
            result.merge_suggestion = report.merge_suggestion
            result.test_suggestions = report.test_suggestions
            result.key_focus_points = report.key_focus_points

            task.summary = report.markdown_summary
            task.risk_level = report.risk_level

        except Exception as e:
            task.status = "FAILED"
            task.error_message = str(e)
            db.commit()
            raise

        return result

    @staticmethod
    async def _update_progress(task: PRReviewTask, db: Session, step: str, progress: int):
        """Update task progress in database"""
        task.status = step
        task.progress = progress
        task.current_step = step
        db.commit()

    def _save_changed_files(self, task_id: int, files: List[ChangedFile], db: Session):
        """Save changed files to database"""
        for f in files:
            db_file = PRChangedFile(
                task_id=task_id,
                file_path=f.file_path,
                change_type=f.change_type,
                additions=f.additions,
                deletions=f.deletions,
                patch=f.patch[:50000] if f.patch else "",
                raw_content=f.raw_content[:50000] if f.raw_content else "",
            )
            db.add(db_file)
        db.commit()

    def _save_findings(self, task_id: int, findings: List[dict], db: Session):
        """Save review findings to database"""
        for f in findings:
            db_finding = PRReviewFinding(
                task_id=task_id,
                file_path=f.get("file", ""),
                line_number=f.get("line"),
                finding_type=f.get("type", ""),
                severity=f.get("severity", "low"),
                title=f.get("title", ""),
                reason=f.get("reason", ""),
                suggestion=f.get("suggestion", ""),
                confidence=f.get("confidence", 0),
            )
            db.add(db_finding)
        db.commit()

    def _run_static_scan(self, changed_files: List[ChangedFile]) -> Dict[str, List[RuleFinding]]:
        """Run static rules on all changed files"""
        findings_by_file = {}
        for f in changed_files:
            if f.change_type != "removed" and f.raw_content:
                findings = self.scanner.scan_file(f.file_path, f.raw_content)
                if findings:
                    findings_by_file[f.file_path] = findings
        return findings_by_file

    async def _summarize_pr(self, pr_info: PRInfo, files: List[ChangedFile]) -> dict:
        """Stage 1: PR summary generation"""
        files_summary = "\n".join([
            f"{f.file_path} ({f.change_type}, +{f.additions}/-{f.deletions})"
            for f in files[:50]
        ])

        # Run AI call in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None,
            self.ai.summarize_pr,
            pr_info.title,
            pr_info.description,
            "",
            files_summary,
        )
        return summary

    async def _review_files(
        self,
        changed_files: List[ChangedFile],
        context: ReviewContext,
        rule_findings: Dict[str, List[RuleFinding]],
    ) -> List[dict]:
        """Stage 2: File-level analysis"""
        all_findings = []
        loop = asyncio.get_event_loop()

        # Filter to files that have content for review (not removed, not trivial)
        review_files = [f for f in changed_files
                        if f.change_type != "removed" and
                        f.patch and
                        f.file_path not in (".gitignore", "package-lock.json", "yarn.lock")]

        for f in review_files:
            related_ctx = ""
            if f.file_path in context.file_relations:
                related_parts = []
                for r_path in context.file_relations[f.file_path]:
                    if r_path in context.related_file_context:
                        related_parts.append(f"--- {r_path} ---\n{context.related_file_context[r_path][:2000]}")
                related_ctx = "\n".join(related_parts)

            rule_text = ""
            if f.file_path in rule_findings:
                rule_text = "\n".join([
                    f"[{rf.severity}] {rf.rule_id}: {rf.message} (line {rf.line_number})"
                    for rf in rule_findings[f.file_path]
                ])

            try:
                file_result = await loop.run_in_executor(
                    None,
                    self.ai.review_file,
                    f.file_path,
                    f.patch,
                    f.raw_content or "",
                    related_ctx,
                    rule_text,
                )
                findings = file_result.get("findings", [])
                for fd in findings:
                    fd["file"] = fd.get("file", f.file_path)
                    fd["line"] = fd.get("line", 0)
                all_findings.extend(findings)
            except Exception as e:
                print(f"Error reviewing {f.file_path}: {e}")

        return all_findings

    async def _cross_file_analysis(
        self,
        changed_files: List[ChangedFile],
        context: ReviewContext,
        file_findings: List[dict],
    ) -> List[dict]:
        """Stage 3: Cross-file consistency analysis"""
        loop = asyncio.get_event_loop()

        # Collect file contents for cross-file analysis
        file_contexts = {}
        for f in changed_files[:15]:  # Limit to 15 files to avoid token overflow
            if f.raw_content:
                file_contexts[f.file_path] = f.raw_content[:5000]

        if len(file_contexts) < 2:
            return []

        try:
            result = await loop.run_in_executor(
                None,
                self.ai.cross_file_analysis,
                file_contexts,
            )
            return result.get("findings", [])
        except Exception as e:
            print(f"Error in cross-file analysis: {e}")
            return []

    def _merge_findings(
        self,
        file_findings: List[dict],
        cross_findings: List[dict],
        rule_findings: Dict[str, List[RuleFinding]],
    ) -> List[dict]:
        """Stage 4: Merge and deduplicate findings across all stages.
        Dedup rules:
        - Same type + same root cause + same module = merge (keep highest severity)
        - Same file + adjacent lines with same issue type = merge
        """
        merged = []

        # Add rule findings as dicts
        for file_path, findings in rule_findings.items():
            for rf in findings:
                merged.append({
                    "file": file_path,
                    "line": rf.line_number,
                    "type": rf.rule_id,
                    "severity": rf.severity,
                    "title": rf.message,
                    "reason": rf.message,
                    "suggestion": "",
                    "confidence": 0.7 if rf.severity in ("critical", "high") else 0.5,
                    "source": "static_rule",
                })

        # Add AI findings
        for fd in file_findings:
            fd["source"] = "ai_file"
            merged.append(fd)

        # Add cross-file findings
        for fd in cross_findings:
            fd["file"] = ", ".join(fd.get("files_involved", []))
            fd["source"] = "ai_cross"
            merged.append(fd)

        # Deduplicate: simple title-based dedup for MVP
        seen_titles = set()
        deduped = []
        for fd in sorted(merged, key=lambda x: self._severity_score(x.get("severity", "low")), reverse=True):
            title = fd.get("title", "").lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                deduped.append(fd)

        return deduped

    @staticmethod
    def _severity_score(severity: str) -> int:
        return {"critical": 5, "high": 4, "medium": 3, "low": 2}.get(severity, 1)
