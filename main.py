import uvicorn
from functools import lru_cache
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import settings
from app.database import init_db, get_db, SessionLocal
from app.golden_evaluation import run_golden_evaluation, run_real_pr_replay_evaluation
from app.models import PRReviewTask, PRChangedFile, PRReviewFinding
from app.rule_catalog import get_rule_catalog
from app.routers import evaluation, tasks, reports
from app.system_status import build_system_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Review Cockpit",
    description="Evidence-driven PR risk analysis cockpit — hybrid rule + AI review engine",
    version="1.2.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# API routers
app.include_router(tasks.router)
app.include_router(reports.router)
app.include_router(evaluation.router)

# Templates
templates = Jinja2Templates(directory="templates")
import json
templates.env.filters["from_json"] = lambda s: json.loads(s) if s else []


@lru_cache(maxsize=1)
def cached_golden_evaluation():
    return run_golden_evaluation()


@lru_cache(maxsize=1)
def cached_real_pr_replay_evaluation():
    return run_real_pr_replay_evaluation()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "golden_eval": cached_golden_evaluation(),
        "real_pr_replay": cached_real_pr_replay_evaluation(),
        "system_status": build_system_status(),
    })


@app.get("/api/system/status")
def system_status():
    return build_system_status()


@app.get("/evaluation", response_class=HTMLResponse)
def evaluation_page(request: Request):
    report = cached_golden_evaluation()
    real_pr_report = cached_real_pr_replay_evaluation()
    ordinary_baseline_count = report.expected_total + report.false_positive_count
    gate_filtered_count = max(0, ordinary_baseline_count - report.visible_expected_count)
    return templates.TemplateResponse("evaluation.html", {
        "request": request,
        "golden_eval": report,
        "real_pr_replay": real_pr_report,
        "ordinary_baseline_count": ordinary_baseline_count,
        "gate_filtered_count": gate_filtered_count,
    })


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
                     "MERGING_RESULTS", "GENERATING_REPORT", "COMMENTED",
                     "COMMENT_UPDATED", "COMMENT_FAILED", "DRY_RUN"]

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


@app.get("/rules", response_class=HTMLResponse)
def rules_page(request: Request):
    rules = get_rule_catalog()
    return templates.TemplateResponse("rules.html", {"request": request, "rules": rules})


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

        SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        findings = db.query(PRReviewFinding).filter(
            PRReviewFinding.task_id == task_id
        ).all()
        findings.sort(
            key=lambda f: (SEVERITY_RANK.get(f.severity.lower() if f.severity else "low", 0),
                           float(f.confidence) if f.confidence else 0),
            reverse=True,
        )

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

        github_ready = sum(1 for f in findings
                           if (f.confidence or 0) >= 0.80
                           or (f.severity in ("critical", "high") and (f.confidence or 0) >= 0.70))

        if counts["critical"] > 0:
            review_decision = "Block merge"
            decision_reason = f"存在 {counts['critical']} 个 critical 问题，禁止合并"
        elif counts["high"] > 0:
            review_decision = "Fix before merge"
            decision_reason = f"存在 {counts['high']} 个 high 问题，建议修复后再合并"
        elif counts["medium"] > 0:
            review_decision = "Review recommended"
            decision_reason = f"存在 {counts['medium']} 个 medium 风险项，建议确认后合并"
        else:
            review_decision = "Ready to merge"
            decision_reason = "未发现高置信阻塞问题"

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
            "cockpit_metrics": {
                "raw_count": task.raw_finding_count or max(len(findings), 1),
                "deduped_count": task.deduped_finding_count or len(findings),
                "visible_count": task.visible_finding_count or len(findings),
                "github_ready": task.github_ready_count or github_ready,
                "invalid_count": task.invalid_finding_count or 0,
                "review_decision": review_decision,
                "decision_reason": decision_reason,
            },
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
