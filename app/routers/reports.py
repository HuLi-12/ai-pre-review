from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PRReviewTask, PRChangedFile, PRReviewFinding, PRReviewFeedback
from app.report_generator import Report, ReportGenerator
from app.schemas import ReportResponse, FindingItem, FeedbackRequest
from app.finding_suggestions import hydrate_missing_suggestions

router = APIRouter(prefix="/api", tags=["reports"])

SEVERITY_RANK = {
    "critical": 4, "high": 3, "medium": 2, "low": 1,
}


@router.get("/tasks/{task_id}/report", response_model=ReportResponse)
def get_report(task_id: int, db: Session = Depends(get_db)):
    """Get the review report for a task"""
    task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "DONE":
        raise HTTPException(status_code=400, detail=f"Task not completed yet, current status: {task.status}")

    findings = db.query(PRReviewFinding).filter(
        PRReviewFinding.task_id == task_id
    ).all()
    hydrate_missing_suggestions(findings)

    # Sort by severity rank (not string), then confidence desc
    findings.sort(
        key=lambda f: (SEVERITY_RANK.get(f.severity.lower() if f.severity else "low", 0),
                       float(f.confidence) if f.confidence else 0),
        reverse=True,
    )

    # Derive merge_suggestion and focus points from findings
    severities = [f.severity.lower() if f.severity else "low" for f in findings]
    has_critical = "critical" in severities
    has_high = "high" in severities
    has_medium = "medium" in severities

    if has_critical:
        merge_suggestion = "建议修复 critical 及以上风险后再合并"
    elif has_high:
        merge_suggestion = "建议修复 high 及以上风险后再合并"
    elif has_medium:
        merge_suggestion = "建议 review medium 风险项，确认后合并"
    else:
        merge_suggestion = "可安全合并"

    test_suggestions = [
        f.suggestion for f in findings
        if f.finding_type == "S015" or (f.title and "test" in f.title.lower())
    ]

    key_focus_points = [
        f.title for f in findings
        if f.severity in ("critical", "high") and f.title
    ]

    return ReportResponse(
        task_id=task.id,
        summary=task.summary,
        risk_level=task.risk_level or "LOW",
        merge_suggestion=merge_suggestion,
        test_suggestions=test_suggestions[:5],
        key_focus_points=key_focus_points[:10],
        raw_finding_count=task.raw_finding_count or 0,
        deduped_finding_count=task.deduped_finding_count or 0,
        visible_finding_count=task.visible_finding_count or len(findings),
        github_ready_count=task.github_ready_count or 0,
        invalid_finding_count=task.invalid_finding_count or 0,
        findings=[FindingItem(
            id=f.id,
            file_path=f.file_path,
            line_number=f.line_number,
            finding_type=f.finding_type,
            severity=f.severity,
            title=f.title,
            reason=f.reason,
            suggestion=f.suggestion,
            confidence=float(f.confidence) if f.confidence else None,
            evidence_json=f.evidence_json,
        ) for f in findings if f.title],
    )


@router.get("/tasks/{task_id}/files")
def get_task_files(task_id: int, db: Session = Depends(get_db)):
    """Get changed files for a task"""
    task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    files = db.query(PRChangedFile).filter(
        PRChangedFile.task_id == task_id
    ).order_by(PRChangedFile.risk_score.desc()).all()

    return [
        {
            "id": f.id,
            "file_path": f.file_path,
            "change_type": f.change_type,
            "additions": f.additions,
            "deletions": f.deletions,
            "risk_level": f.risk_level,
            "risk_score": f.risk_score,
        }
        for f in files
    ]


@router.get("/tasks/{task_id}/file/{file_id}/findings")
def get_file_findings(task_id: int, file_id: int, db: Session = Depends(get_db)):
    """Get findings for a specific file"""
    findings = db.query(PRReviewFinding).filter(
        PRReviewFinding.task_id == task_id,
        PRReviewFinding.file_id == file_id,
    ).all()
    hydrate_missing_suggestions(findings)

    findings.sort(
        key=lambda f: (SEVERITY_RANK.get(f.severity.lower() if f.severity else "low", 0),
                       f.line_number or 0),
        reverse=True,
    )

    return [
        {
            "id": f.id,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "title": f.title,
            "reason": f.reason,
            "suggestion": f.suggestion,
            "confidence": float(f.confidence) if f.confidence else None,
            "evidence_json": f.evidence_json,
            "status": f.status,
        }
        for f in findings
    ]


@router.post("/findings/{finding_id}/feedback")
def submit_feedback(finding_id: int, req: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit feedback on a finding (false positive / effective / resolved)"""
    finding = db.query(PRReviewFinding).filter(PRReviewFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    feedback = PRReviewFeedback(
        finding_id=finding_id,
        feedback_type=req.feedback_type,
        comment=req.comment,
    )
    db.add(feedback)

    if req.feedback_type == "RESOLVED":
        finding.status = "RESOLVED"
    elif req.feedback_type == "FALSE_POSITIVE":
        finding.status = "DISMISSED"

    db.commit()
    return {"status": "ok"}


@router.get("/tasks/{task_id}/comment-preview")
def preview_comment(task_id: int, db: Session = Depends(get_db)):
    """Preview the GitHub comment that would be posted (safe, no side effects)."""
    task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "DONE":
        raise HTTPException(status_code=400, detail=f"Task not completed, status: {task.status}")

    findings = db.query(PRReviewFinding).filter(
        PRReviewFinding.task_id == task_id
    ).all()
    hydrate_missing_suggestions(findings)

    # Reconstruct a Report from DB findings
    by_severity = {"critical": [], "high": [], "medium": [], "low": []}
    for f in findings:
        raw_confidence = float(f.confidence) if f.confidence else 0
        fd = {
            "file": f.file_path,
            "line": f.line_number,
            "type": f.finding_type,
            "severity": (f.severity or "low").lower(),
            "title": f.title,
            "reason": f.reason or "",
            "suggestion": f.suggestion or "",
            "confidence": raw_confidence,
            "github_ready": (
                raw_confidence >= 0.80
                or (f.severity in ("critical", "high") and raw_confidence >= 0.70)
            ),
        }
        sev = fd["severity"]
        if sev in by_severity:
            by_severity[sev].append(fd)

    report = Report(
        risk_level=task.risk_level or "LOW",
        merge_suggestion="",
        markdown_summary=task.summary or "",
        findings_by_severity=by_severity,
    )

    comment_markdown = ReportGenerator.generate_github_comment(report)
    github_ready_count = sum(1 for f in findings if (
        (f.confidence or 0) >= 0.80
        or (f.severity in ("critical", "high") and (f.confidence or 0) >= 0.70)
    ))

    return {
        "task_id": task_id,
        "comment_markdown": comment_markdown,
        "github_ready_count": github_ready_count,
        "total_findings": len(findings),
        "dry_run": bool(task.dry_run),
    }
