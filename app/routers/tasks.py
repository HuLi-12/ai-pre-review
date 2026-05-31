import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import PRReviewTask
from app.schemas import CreateTaskRequest, TaskResponse
from app.github_client import GitHubClient
from app.review_engine import ReviewEngine

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

TERMINAL_REVIEW_STEPS = {
    "DRY_RUN",
    "COMMENTED",
    "COMMENT_UPDATED",
    "COMMENT_FAILED",
}


@router.post("", response_model=TaskResponse)
async def create_task(req: CreateTaskRequest, db: Session = Depends(get_db)):
    """Create a new PR review task"""
    try:
        owner, repo, number = GitHubClient.parse_pr_url(req.pr_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task = PRReviewTask(
        repo_owner=owner,
        repo_name=repo,
        pr_number=number,
        pr_url=req.pr_url,
        auto_comment=req.auto_comment,
        dry_run=1 if req.dry_run else 0,
        status="PENDING",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Start async review in background with its own session
    asyncio.create_task(_run_review_async(task.id, req.github_token))

    return TaskResponse(
        task_id=task.id,
        status=task.status,
        progress=0,
        current_step="PENDING",
    )


async def _run_review_async(task_id: int, github_token: Optional[str]):
    """Run review in background with dedicated DB session"""
    db = SessionLocal()
    try:
        task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
        if not task:
            return

        engine = ReviewEngine(github_token=github_token)
        await engine.run_review(task, db)

        _mark_task_done(task)
        db.commit()
    except Exception as e:
        try:
            task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
            if task:
                task.status = "FAILED"
                if not task.error_type:
                    task.error_type = "INTERNAL_ERROR"
                if not task.error_message:
                    task.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _mark_task_done(task: PRReviewTask):
    task.status = "DONE"
    task.progress = 100
    if task.current_step not in TERMINAL_REVIEW_STEPS:
        task.current_step = "COMPLETED"


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get task status by ID"""
    task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        current_step=task.current_step,
        error_type=task.error_type,
        error_message=task.error_message,
        fallback_flags=task.fallback_flags,
        pipeline_details=task.pipeline_details,
    )
