import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import settings
from app.database import init_db, get_db, SessionLocal
from app.models import PRReviewTask, PRChangedFile, PRReviewFinding
from app.routers import tasks, reports

app = FastAPI(
    title="AI Code Review",
    description="AI-powered GitHub PR review tool",
    version="1.0.0",
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# API routers
app.include_router(tasks.router)
app.include_router(reports.router)

# Templates
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/tasks", response_class=HTMLResponse)
def task_history(request: Request, page: int = 1, q: str = "", status: str = ""):
    db = SessionLocal()
    try:
        query = db.query(PRReviewTask)
        if q:
            query = query.filter(PRReviewTask.pr_url.ilike(f"%{q}%"))
        if status:
            query = query.filter(PRReviewTask.status == status)

        total = query.count()
        per_page = 20
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        tasks = query.order_by(PRReviewTask.created_at.desc()).offset(offset).limit(per_page).all()
        statuses = ["PENDING", "DONE", "FAILED", "FETCHING_PR", "BUILDING_CONTEXT",
                     "STATIC_SCAN", "AI_PR_SUMMARY", "AI_FILE_REVIEW", "AI_CROSS_FILE",
                     "MERGING_RESULTS", "GENERATING_REPORT", "COMMENTED"]

        return templates.TemplateResponse("task_history.html", {
            "request": request,
            "tasks": tasks,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "q": q,
            "status_filter": status,
            "statuses": statuses,
        })
    finally:
        db.close()


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_progress(request: Request, task_id: int):
    db = SessionLocal()
    try:
        task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
        if not task:
            return HTMLResponse("Task not found", status_code=404)
        return templates.TemplateResponse("task_progress.html", {
            "request": request,
            "task": task,
        })
    finally:
        db.close()


@app.get("/tasks/{task_id}/report", response_class=HTMLResponse)
def view_report(request: Request, task_id: int):
    db = SessionLocal()
    try:
        task = db.query(PRReviewTask).filter(PRReviewTask.id == task_id).first()
        if not task:
            return HTMLResponse("Task not found", status_code=404)

        if task.status != "DONE":
            return RedirectResponse(url=f"/tasks/{task_id}")

        findings = db.query(PRReviewFinding).filter(
            PRReviewFinding.task_id == task_id
        ).order_by(
            PRReviewFinding.severity.desc(),
            PRReviewFinding.confidence.desc()
        ).all()

        files = db.query(PRChangedFile).filter(
            PRChangedFile.task_id == task_id
        ).all()

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.severity.lower() if f.severity else "low"
            if sev in counts:
                counts[sev] += 1

        key_focus = [f.title for f in findings if f.severity in ("critical", "high")]

        merge_suggestion = "建议修复 high 及以上风险后再合并"
        if not findings:
            merge_suggestion = "可安全合并"
        elif all(f.severity in ("medium", "low") for f in findings if f.severity):
            merge_suggestion = "建议 review 后合并"

        return templates.TemplateResponse("report.html", {
            "request": request,
            "task": task,
            "findings": findings,
            "files": files,
            "counts": counts,
            "summary": task.summary,
            "report": {
                "risk_level": task.risk_level or "LOW",
                "merge_suggestion": merge_suggestion,
            },
            "key_focus_points": key_focus[:10],
        })
    finally:
        db.close()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
