import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PRReviewTask
from app.schemas import CreateTaskRequest, TaskResponse
from app.github_client import GitHubClient
from app.review_engine import ReviewEngine

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


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
        status="PENDING",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Start async review in background
    asyncio.create_task(_run_review_async(task.id, req.github_token, db))

    return TaskResponse(
        task_id=task.id,
        status=task.status,
        progress=0,
        current_step="PENDING",
    )


async def _run_review_async(task_id: int, github_token: Optional[str], db: Session):
    """Run review in background"""
    task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
    if not task:
        return

    engine = ReviewEngine(github_token=github_token)
    try:
        await engine.run_review(task, db)
        task.status = "DONE"
        task.progress = 100
        task.current_step = "COMPLETED"
    except Exception as e:
        task.status = "FAILED"
        task.error_message = str(e)
    finally:
        db.commit()


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
    )
