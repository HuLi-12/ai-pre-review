import asyncio
import json
import re
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field

import httpx
from sqlalchemy.orm import Session

from app.github_client import GitHubClient, ChangedFile, PRInfo
from app.static_scanner import StaticScanner, RuleFinding
from app.diff_utils import parse_patch
from app.context_builder import ContextBuilder, ReviewContext
from app.ai_client import AIClient
from app.models import PRReviewTask, PRChangedFile, PRReviewFinding
from app.report_generator import ReportGenerator
from app.risk_scorer import FileRiskScorer
from app.confidence_calculator import calculate_confidence, should_show_in_report, should_comment_to_github
from app.rule_catalog import get_rule_suggestion


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
    raw_finding_count: int = 0
    deduped_finding_count: int = 0
    visible_finding_count: int = 0
    github_ready_count: int = 0
    invalid_finding_count: int = 0


class ReviewEngine:
    """Multi-stage AI Review orchestration engine with risk-based prioritization."""

    AI_SEVERITIES = {"critical", "high", "medium", "low"}

    def __init__(self, github_token: Optional[str] = None):
        self.github = GitHubClient(token=github_token)
        self.scanner = StaticScanner()
        self.ai = AIClient()
        self.report_gen = ReportGenerator()
        self.risk_scorer = FileRiskScorer()

    async def run_review(self, task: PRReviewTask, db: Session) -> ReviewResult:
        """Execute full review pipeline"""
        result = ReviewResult()
        owner, repo, number = task.repo_owner, task.repo_name, task.pr_number
        fallbacks = {}
        pipeline_stages = []

        try:
            # ---- Stage 1: Fetch PR Info ----
            await self._update_progress(task, db, "FETCHING_PR", 10)
            pr_info = self.github.get_pr_info(owner, repo, number)
            changed_files = self.github.get_changed_files(owner, repo, number, head_sha=pr_info.commit_sha)
            task.commit_sha = pr_info.commit_sha

            pipeline_stages.append("FETCHING_PR")
            if "public diff fallback" in (pr_info.description or "").lower():
                fallbacks["public_diff"] = True

            # Save changed files to DB
            self._save_changed_files(task.id, changed_files, db)

            # ---- Stage 2: Build Context ----
            await self._update_progress(task, db, "BUILDING_CONTEXT", 20)
            context_builder = ContextBuilder(
                self.github,
                owner,
                repo,
                ref=pr_info.commit_sha or pr_info.source_branch or "main",
            )
            review_context = context_builder.build(changed_files)

            # ---- Stage 3: Static Rule Scanning (on patch only) ----
            await self._update_progress(task, db, "STATIC_SCAN", 30)
            rule_findings = self._run_static_scan(changed_files)
            self._changed_line_index = self._build_changed_line_index(changed_files)
            pipeline_stages.append("STATIC_SCAN")

            # ---- Stage 4: Risk Scoring & AI Review ----
            await self._update_progress(task, db, "AI_PR_SUMMARY", 40)
            summary = await self._summarize_pr(pr_info, changed_files)
            pipeline_stages.append("AI_PR_SUMMARY")
            if summary.get("one_line_summary", "").startswith("AI summary unavailable"):
                fallbacks["ai_summary"] = True

            # File-level analysis with risk-based prioritization
            await self._update_progress(task, db, "AI_FILE_REVIEW", 55)
            file_findings = await self._review_files_prioritized(
                changed_files, review_context, rule_findings
            )
            pipeline_stages.append("AI_FILE_REVIEW")

            # Cross-file analysis (only if enough files changed)
            await self._update_progress(task, db, "AI_CROSS_FILE", 70)
            cross_findings = await self._cross_file_analysis(changed_files, review_context, file_findings)
            pipeline_stages.append("AI_CROSS_FILE")

            # ---- Stage 5: Merge, Dedup & Confidence ----
            await self._update_progress(task, db, "MERGING_RESULTS", 85)
            merged = self._merge_findings(file_findings, cross_findings, rule_findings)
            pipeline_stages.append("MERGING_RESULTS")

            # Persist real pipeline metrics
            counts = getattr(self, '_pipeline_counts', {})
            task.raw_finding_count = counts.get("raw", 0)
            task.deduped_finding_count = counts.get("deduped", 0)
            task.visible_finding_count = counts.get("visible", len(merged))
            task.github_ready_count = counts.get("github_ready", 0)
            task.invalid_finding_count = counts.get("invalid", 0)

            # ---- Stage 6: Generate Report ----
            await self._update_progress(task, db, "GENERATING_REPORT", 95)
            report = self.report_gen.generate(summary, merged)
            pipeline_stages.append("GENERATING_REPORT")

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
            result.raw_finding_count = counts.get("raw", 0)
            result.deduped_finding_count = counts.get("deduped", 0)
            result.visible_finding_count = counts.get("visible", len(merged))
            result.github_ready_count = counts.get("github_ready", 0)
            result.invalid_finding_count = counts.get("invalid", 0)

            task.summary = report.markdown_summary
            task.risk_level = report.risk_level
            pipeline_stages.append("DONE")
            task.fallback_flags = json.dumps(fallbacks) if fallbacks else None
            task.pipeline_details = json.dumps(pipeline_stages) if pipeline_stages else None
            db.commit()

            # ---- Stage 7: Auto Comment to GitHub (if enabled) ----
            if task.auto_comment and merged:
                if task.dry_run:
                    task.current_step = "DRY_RUN"
                    db.commit()
                else:
                    try:
                        comment = self.report_gen.generate_github_comment(report)

                        # Marker-based lookup (most robust — survives comment deletion)
                        if not task.comment_id:
                            task.comment_id = self.github.find_pr_comment_by_marker(
                                owner, repo, number, ReportGenerator.COMMENT_MARKER
                            )
                        # Fallback: DB-based lookup (previous task's comment_id for same PR)
                        if not task.comment_id:
                            task.comment_id = self._find_reusable_comment_id(task, db)

                        if task.comment_id:
                            ok = self.github.update_pr_comment(owner, repo, task.comment_id, comment)
                            task.current_step = "COMMENT_UPDATED" if ok else "COMMENT_FAILED"
                        else:
                            comment_id = self.github.create_pr_comment(owner, repo, number, comment)
                            if comment_id:
                                task.comment_id = comment_id
                                task.current_step = "COMMENTED"
                            else:
                                task.current_step = "COMMENT_FAILED"
                        db.commit()
                    except Exception as e:
                        print(f"Failed to post GitHub comment: {e}")

        except Exception as e:
            task.status = "FAILED"
            task.error_type = self._categorize_error(e, task.current_step)
            task.error_message = str(e)[:500]
            if fallbacks:
                task.fallback_flags = json.dumps(fallbacks)
            if pipeline_stages:
                pipeline_stages.append(f"FAILED:{task.error_type}")
                task.pipeline_details = json.dumps(pipeline_stages)
            db.commit()
            raise

        return result

    @staticmethod
    async def _update_progress(task: PRReviewTask, db: Session, step: str, progress: int):
        task.status = step
        task.progress = progress
        task.current_step = step
        db.commit()

    @staticmethod
    def _categorize_error(error: Exception, step: Optional[str]) -> str:
        """Categorize an exception into a stable error type for task.error_type."""
        if isinstance(error, httpx.TimeoutException):
            return "NETWORK_TIMEOUT"
        if isinstance(error, httpx.ConnectError):
            return "NETWORK_ERROR"
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            message = ""
            try:
                message = str(error.response.json().get("message", ""))
            except Exception:
                message = getattr(error.response, "text", "") or ""
            message_lower = message.lower()
            if status == 401:
                return "GITHUB_AUTH_ERROR"
            if status == 403:
                remaining = error.response.headers.get("X-RateLimit-Remaining")
                if remaining == "0" or "rate limit" in message_lower:
                    return "GITHUB_RATE_LIMIT"
                if (
                    "resource not accessible" in message_lower
                    or "permission" in message_lower
                    or "must have" in message_lower
                    or "forbidden" in message_lower
                ):
                    return "GITHUB_PERMISSION_ERROR"
                return "GITHUB_FORBIDDEN"
            if status == 404:
                return "GITHUB_NOT_FOUND_OR_PRIVATE"
            return "GITHUB_API_ERROR"
        if isinstance(error, httpx.RequestError):
            return "NETWORK_ERROR"
        if isinstance(error, ValueError):
            return "VALIDATION_ERROR"
        if step and step.startswith("AI_"):
            return "AI_PROVIDER_ERROR"
        return "INTERNAL_ERROR"

    @staticmethod
    def _find_reusable_comment_id(task: PRReviewTask, db: Session) -> Optional[int]:
        previous = (
            db.query(PRReviewTask)
            .filter(PRReviewTask.repo_owner == task.repo_owner)
            .filter(PRReviewTask.repo_name == task.repo_name)
            .filter(PRReviewTask.pr_number == task.pr_number)
            .filter(PRReviewTask.comment_id.isnot(None))
            .filter(PRReviewTask.id != task.id)
            .order_by(PRReviewTask.updated_at.desc(), PRReviewTask.id.desc())
            .first()
        )
        return previous.comment_id if previous else None

    def _save_changed_files(self, task_id: int, files: List[ChangedFile], db: Session):
        """Save changed files and build file_path -> file_id mapping."""
        file_map = {}
        for f in files:
            risk = self.risk_scorer.score(f)
            db_file = PRChangedFile(
                task_id=task_id,
                file_path=f.file_path,
                change_type=f.change_type,
                additions=f.additions,
                deletions=f.deletions,
                patch=f.patch[:50000] if f.patch else "",
                raw_content=f.raw_content[:50000] if f.raw_content else "",
                risk_level=risk["level"],
                risk_score=risk["score"],
            )
            db.add(db_file)
            db.flush()  # Get the ID before commit
            file_map[f.file_path] = db_file.id
        db.commit()
        self._file_map = file_map  # Store for _save_findings

    def _save_findings(self, task_id: int, findings: List[dict], db: Session):
        import json
        file_map = getattr(self, '_file_map', {})
        for f in findings:
            confidence = f.get("confidence", 0)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except (ValueError, TypeError):
                    confidence = 0.0
            file_path = f.get("file", "")
            source = f.get("source", "ai_file")
            rule_id = f.get("rule_id") or (f.get("type") if source == "static_rule" else None)
            category = f.get("category") or (None if source == "static_rule" else f.get("type", source))
            if source == "static_rule":
                review_source = f"Static Rule {rule_id}"
            elif source == "ai_cross":
                review_source = f"AI Cross-file Review {category}"
            else:
                review_source = f"AI File Review {category}"

            # Build evidence chain
            evidence = []
            evidence.append({
                "type": "changed_file",
                "label": "Changed File",
                "content": file_path,
            })
            evidence.append({
                "type": "review_source",
                "label": "Review Source",
                "content": review_source,
            })
            if f.get("line"):
                evidence.append({
                    "type": "line_number",
                    "label": "Line",
                    "content": str(f.get("line")),
                })
            if f.get("line_content"):
                evidence.append({
                    "type": "code_snippet",
                    "label": "Code",
                    "content": f.get("line_content", "")[:240],
                })
            finding_type = rule_id if source == "static_rule" else (category or source)
            if source == "static_rule" and rule_id:
                evidence.append({
                    "type": "rule_match",
                    "label": "Static Rule",
                    "content": f"{rule_id}: {f.get('title', '')}",
                })
            else:
                evidence.append({
                    "type": "ai_source",
                    "label": "AI Source",
                    "content": source,
                })
            severity = f.get("severity", "low")
            conf_pct = int(confidence * 100) if confidence else 0
            conf_label = "visible + GitHub-ready" if confidence >= 0.8 else \
                         "visible in report" if confidence >= 0.6 else "filtered by default"
            evidence.append({
                "type": "confidence",
                "label": "Confidence Gate",
                "content": f"{conf_pct}% ({severity}) — {conf_label}",
            })

            if f.get("confidence_reason"):
                evidence.append({
                    "type": "confidence_reason",
                    "label": "Confidence Reason",
                    "content": f.get("confidence_reason", ""),
                })

            db_finding = PRReviewFinding(
                task_id=task_id,
                file_id=file_map.get(file_path),
                file_path=file_path,
                line_number=f.get("line"),
                finding_type=finding_type,
                severity=severity,
                title=f.get("title", ""),
                reason=f.get("reason", ""),
                suggestion=f.get("suggestion", ""),
                confidence=confidence,
                evidence_json=json.dumps(evidence, ensure_ascii=False),
            )
            db.add(db_finding)
        db.commit()

    # ---- Static Scan ----

    def _run_static_scan(self, changed_files: List[ChangedFile]) -> Dict[str, List[RuleFinding]]:
        """Run static rules on changed files — only scans patch added lines."""
        # Also check test files changed for S015
        source_changed = False
        test_changed = False

        findings_by_file = {}
        for f in changed_files:
            if f.change_type == "removed":
                continue

            # Track test coverage for S015
            if "test" in f.file_path.lower():
                test_changed = True
            elif f.file_path.endswith((".java", ".py", ".ts", ".js", ".go")):
                source_changed = True

            # Scan only the patch (added lines), not full raw content
            if f.patch:
                findings = self.scanner.scan_patch(f.file_path, f.patch, f.raw_content or "")
                if findings:
                    findings_by_file[f.file_path] = findings

        # Add S015 if source changed but no test file changed
        if source_changed and not test_changed:
            # Attach to a relevant source file or general
            s015 = RuleFinding(
                file_path="(project-wide)",
                line_number=0,
                rule_id="S015",
                severity="medium",
                message="Core source files changed but no test files were updated — consider adding tests",
            )
            # Add to an existing file's findings
            if findings_by_file:
                first_key = next(iter(findings_by_file))
                findings_by_file[first_key].append(s015)
            else:
                # Create a pseudo entry
                findings_by_file["(project)"] = [s015]

        return findings_by_file

    # ---- PR Summary ----

    async def _summarize_pr(self, pr_info: PRInfo, files: List[ChangedFile]) -> dict:
        files_summary = "\n".join([
            f"{f.file_path} ({f.change_type}, +{f.additions}/-{f.deletions})"
            for f in files[:50]
        ])
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

    # ---- Risk-Based File Review ----

    async def _review_files_prioritized(
        self,
        changed_files: List[ChangedFile],
        context: ReviewContext,
        rule_findings: Dict[str, List[RuleFinding]],
    ) -> List[dict]:
        """Review files in order of risk score. Deep review for high-risk files."""
        all_findings = []
        loop = asyncio.get_event_loop()

        # Score and sort files
        scored_files = []
        for f in changed_files:
            if f.change_type == "removed" or not f.patch:
                continue
            if f.file_path in (".gitignore", "package-lock.json", "yarn.lock"):
                continue
            risk = self.risk_scorer.score(f)
            depth = self.risk_scorer.get_analysis_depth(f)
            if depth == "skip":
                continue
            scored_files.append((f, risk, depth))

        # Sort by score descending (highest risk first)
        scored_files.sort(key=lambda x: x[1]["score"], reverse=True)

        for f, risk, depth in scored_files:
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

            # For normal risk files, use summary context; for high risk, deep analysis
            try:
                if depth == "deep":
                    file_result = await loop.run_in_executor(
                        None,
                        self.ai.review_file,
                        f.file_path,
                        f.patch,
                        f.raw_content or "",
                        related_ctx,
                        rule_text,
                    )
                else:
                    # Normal: use fast model with less context
                    file_result = await loop.run_in_executor(
                        None,
                        self.ai.review_file,
                        f.file_path,
                        f.patch,
                        f.raw_content[:5000] if f.raw_content else "",
                        related_ctx[:2000],
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

    # ---- Cross-File Analysis ----

    async def _cross_file_analysis(
        self,
        changed_files: List[ChangedFile],
        context: ReviewContext,
        file_findings: List[dict],
    ) -> List[dict]:
        loop = asyncio.get_event_loop()

        file_contexts = {}
        for f in changed_files[:15]:
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

    # ---- Merge & Dedup ----

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize a finding title for comparison."""
        t = title.lower().strip()
        t = re.sub(r'[^a-z0-9一-鿿]', '', t)
        return t[:30]

    @staticmethod
    def _build_signature(finding: dict) -> str:
        """Build a dedup signature for a finding."""
        file_path = finding.get("file", "")
        issue_type = finding.get("type", "") or finding.get("source", "")
        line = finding.get("line", 0) or 0
        title = ReviewEngine._normalize_title(finding.get("title", ""))

        # Bucket line numbers into groups of 10
        line_bucket = line // 10 if isinstance(line, int) else 0

        return f"{file_path}:{issue_type}:{line_bucket}:{title[:20]}"

    @staticmethod
    def _category_for_static_rule(rule_id: str) -> str:
        if rule_id in {"S004", "S005", "S008", "S014"}:
            return "security"
        if rule_id in {"S006", "S009", "S010", "S013"}:
            return "correctness"
        if rule_id in {"S011", "S012"}:
            return "performance"
        if rule_id == "S015":
            return "test"
        return "maintainability"

    @staticmethod
    def _build_changed_line_index(changed_files: List[ChangedFile]) -> Dict[str, Dict[int, str]]:
        """Build file -> added line -> content index for AI evidence anchoring."""
        index: Dict[str, Dict[int, str]] = {}
        for changed_file in changed_files:
            if not changed_file.patch:
                continue
            lines = parse_patch(changed_file.patch)
            if not lines:
                continue
            index[changed_file.file_path] = {
                item["new_line"]: item["content"]
                for item in lines
                if item.get("new_line") is not None
            }
        return index

    @staticmethod
    def _coerce_line_number(line: Any) -> int:
        try:
            return int(line)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _coerce_model_confidence(confidence: Any) -> Optional[float]:
        try:
            value = float(confidence)
        except (TypeError, ValueError):
            return None
        return max(0.0, min(1.0, value))

    def _normalize_ai_file_finding(self, finding: Any) -> Optional[dict]:
        """Validate and normalize a model-produced file finding."""
        if not isinstance(finding, dict):
            return None

        file_path = str(finding.get("file", "")).strip()
        title = str(finding.get("title", "")).strip()
        reason = str(finding.get("reason", "")).strip()
        suggestion = str(finding.get("suggestion", "")).strip()
        severity = str(finding.get("severity", "")).strip().lower()
        line = self._coerce_line_number(finding.get("line"))

        if not file_path or not title or not reason or not suggestion:
            return None
        if severity not in self.AI_SEVERITIES:
            return None
        if line <= 0:
            return None
        if "confidence" not in finding:
            return None

        model_confidence = self._coerce_model_confidence(finding.get("confidence"))
        if model_confidence is None:
            return None

        normalized = dict(finding)
        category = str(finding.get("category") or finding.get("type", "")).strip().lower()
        if not category or category.startswith("s0"):
            category = "correctness"
        normalized.update({
            "file": file_path,
            "line": line,
            "type": category,
            "category": category,
            "rule_id": None,
            "severity": severity,
            "title": title,
            "reason": reason,
            "suggestion": suggestion,
            "model_confidence": model_confidence,
            "source": "ai_file",
        })
        normalized.pop("confidence", None)
        return normalized

    def _attach_changed_line_evidence(self, finding: dict) -> dict:
        """Anchor AI file findings to nearby changed lines when possible."""
        if finding.get("source") != "ai_file":
            return finding

        file_path = finding.get("file", "")
        line = self._coerce_line_number(finding.get("line"))
        if line:
            finding["line"] = line

        changed_lines = getattr(self, "_changed_line_index", {}).get(file_path, {})
        if not changed_lines:
            finding["changed_line_evidence"] = False
            finding["confidence_reason"] = "AI finding has no changed-line evidence for this file"
            return finding

        nearest_line = None
        for candidate in changed_lines:
            if line and abs(candidate - line) <= 3:
                if nearest_line is None or abs(candidate - line) < abs(nearest_line - line):
                    nearest_line = candidate

        if nearest_line is None:
            finding["changed_line_evidence"] = False
            finding["confidence_reason"] = "AI finding cited a line outside the changed hunk"
            return finding

        finding["changed_line_evidence"] = True
        finding["line"] = line or nearest_line
        finding["line_content"] = changed_lines[nearest_line]
        finding["confidence_reason"] = "AI finding anchored to changed-line evidence"
        return finding

    def _merge_findings(
        self,
        file_findings: List[dict],
        cross_findings: List[dict],
        rule_findings: Dict[str, List[RuleFinding]],
    ) -> List[dict]:
        """Merge findings with signature-based dedup, confidence calc, and threshold filtering."""
        merged = []

        # Add rule findings
        for file_path, findings in rule_findings.items():
            for rf in findings:
                merged.append({
                    "file": file_path,
                    "line": rf.line_number,
                    "type": rf.rule_id,
                    "rule_id": rf.rule_id,
                    "category": self._category_for_static_rule(rf.rule_id),
                    "severity": rf.severity,
                    "title": rf.message,
                    "reason": rf.message,
                    "suggestion": get_rule_suggestion(rf.rule_id),
                    "confidence": 0.0,
                    "source": "static_rule",
                    "line_content": rf.line_content,
                    "confidence_reason": "Deterministic static rule match with changed-line evidence",
                })

        invalid_ai_count = 0

        # Add AI file findings
        for fd in file_findings:
            normalized = self._normalize_ai_file_finding(fd)
            if normalized is None:
                invalid_ai_count += 1
                continue
            merged.append(self._attach_changed_line_evidence(normalized))

        # Add cross-file findings
        for fd in cross_findings:
            fd = dict(fd)
            files_involved = fd.get("files_involved", [])
            fd["file"] = ", ".join(files_involved) if isinstance(files_involved, list) else str(files_involved)
            fd["source"] = "ai_cross"
            fd["rule_id"] = None
            fd["category"] = str(fd.get("category") or fd.get("type") or "architecture").strip().lower()
            fd["type"] = fd["category"]
            merged.append(fd)

        # ---- Signature-based dedup ----
        seen: Dict[str, List[dict]] = {}
        for fd in merged:
            sig = self._build_signature(fd)
            if sig not in seen:
                seen[sig] = []
            seen[sig].append(fd)

        # ---- Merge duplicates and calculate confidence ----
        final_findings = []
        for sig, group in seen.items():
            if not group:
                continue

            # Keep the highest severity finding from the group
            group.sort(key=lambda x: self._severity_score(x.get("severity", "low")), reverse=True)
            best = dict(group[0])

            # Check if both AI and rule found the same issue
            has_rule = any(f.get("source") == "static_rule" for f in group)
            has_ai = any(f.get("source", "").startswith("ai") for f in group)

            # For rule-only findings, give them their base confidence
            if best.get("source") == "static_rule":
                best["confidence"] = calculate_confidence(best, has_rule_match=has_rule and has_ai)
            else:
                # Calculate confidence with agreement bonus
                best["confidence"] = calculate_confidence(best, has_rule_match=has_rule)

            # Add cross-reference info
            if has_rule and has_ai:
                best["title"] = best["title"]
                best["reason"] = best.get("reason", "") + " (Confirmed by both static rule and AI analysis)"

            final_findings.append(best)

        # ---- Confidence threshold filtering ----
        filtered = [f for f in final_findings if should_show_in_report(f.get("confidence", 0) or 0)]

        # Mark github_ready flag for each finding (used by report_generator for GitHub comments)
        for f in filtered:
            f["github_ready"] = should_comment_to_github(
                f.get("confidence", 0) or 0,
                f.get("severity", "low"),
            )

        # Save pipeline counts for cockpit metrics
        self._pipeline_counts = {
            "raw": len(merged) + invalid_ai_count,
            "deduped": len(final_findings),
            "visible": len(filtered),
            "github_ready": sum(1 for f in filtered if f["github_ready"]),
            "invalid": invalid_ai_count,
        }

        # Sort by severity then confidence
        filtered.sort(
            key=lambda x: (self._severity_score(x.get("severity", "low")),
                           x.get("confidence", 0) or 0),
            reverse=True,
        )

        return filtered

    @staticmethod
    def _severity_score(severity: str) -> int:
        return {"critical": 5, "high": 4, "medium": 3, "low": 2}.get(severity, 1)
