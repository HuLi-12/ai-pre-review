from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PRReviewTask, PRChangedFile, PRReviewFinding, PRReviewFeedback
from app.schemas import ReportResponse, FindingItem, FeedbackRequest

router = APIRouter(prefix="/api", tags=["reports"])


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
    ).order_by(
        PRReviewFinding.severity.desc(),
        PRReviewFinding.confidence.desc()
    ).all()

    return ReportResponse(
        task_id=task.id,
        summary=task.summary,
        risk_level=task.risk_level,
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
        ) for f in findings],
    )


@router.get("/tasks/{task_id}/files")
def get_task_files(task_id: int, db: Session = Depends(get_db)):
    """Get changed files for a task"""
    task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    files = db.query(PRChangedFile).filter(
        PRChangedFile.task_id == task_id
    ).all()

    return [
        {
            "id": f.id,
            "file_path": f.file_path,
            "change_type": f.change_type,
            "additions": f.additions,
            "deletions": f.deletions,
            "risk_level": f.risk_level,
        }
        for f in files
    ]


@router.get("/tasks/{task_id}/file/{file_id}/findings")
def get_file_findings(task_id: int, file_id: int, db: Session = Depends(get_db)):
    """Get findings for a specific file"""
    findings = db.query(PRReviewFinding).filter(
        PRReviewFinding.task_id == task_id,
        PRReviewFinding.file_id == file_id,
    ).order_by(
        PRReviewFinding.severity.desc(),
        PRReviewFinding.line_number.asc(),
    ).all()

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
