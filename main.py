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
                     "MERGING_RESULTS", "GENERATING_REPORT", "COMMENTED",
                     "COMMENT_UPDATED", "COMMENT_FAILED"]

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
    rules = [
        {"id": "S001", "name": "hardcoded_print", "severity": "high", "description": "检测遗留的调试输出语句，如 print、console.log、System.out.println 等。这些语句不应出现在生产代码中。", "detection": "static", "bad_code": 'print("debug:", data)\nconsole.log("user:", user)', "good_code": "import logging\nlogger = logging.getLogger(__name__)\nlogger.debug(\"user: %s\", user)"},
        {"id": "S002", "name": "todo_fixme", "severity": "low", "description": "检测代码中遗留的 TODO 或 FIXME 注释。建议在合并前确认这些待办项是否已处理。", "detection": "static", "bad_code": "# TODO: handle edge case\n// FIXME: this is a hack", "good_code": "# 已处理或创建 Issue 跟踪"},
        {"id": "S003", "name": "empty_catch", "severity": "high", "description": "检测空的 catch 块。异常被静默吞掉会导致难以排查的 Bug，至少应记录异常信息。", "detection": "static", "bad_code": "try:\n    do_something()\nexcept Exception:\n    pass", "good_code": "try:\n    do_something()\nexcept Exception as e:\n    logger.error(\"failed: %s\", e)"},
        {"id": "S004", "name": "sensitive_log", "severity": "high", "description": "检测是否在日志中记录了敏感信息（密码、密钥、Token 等）。避免将凭据写入日志。", "detection": "static", "bad_code": 'logger.info("password: %s", password)', "good_code": 'logger.info("login success: user=%s", user)'},
        {"id": "S005", "name": "hardcoded_password", "severity": "critical", "description": "检测硬编码的密码、密钥或 API Token。凭据应通过环境变量或密钥管理服务注入。", "detection": "static", "bad_code": 'password = "123456"\napi_key = "sk-xxxxx"', "good_code": "password = os.getenv(\"DB_PASSWORD\")\napi_key = os.getenv(\"API_KEY\")"},
        {"id": "S006", "name": "missing_null_check", "severity": "medium", "description": "检测方法调用结果是否缺少空值检查。由 AI 分析调用链判断可能为空的返回值。", "detection": "ai", "bad_code": "user = get_user(id)\nuser.name  # user may be None", "good_code": "user = get_user(id)\nif user:\n    print(user.name)"},
        {"id": "S007", "name": "large_method", "severity": "medium", "description": "检测被 PR 修改的方法是否过长（超过 80 行）。过长的方法应当拆分为多个小函数。", "detection": "static", "bad_code": "# > 80 lines in one method", "good_code": "# Split into smaller helper functions"},
        {"id": "S008", "name": "missing_auth_check", "severity": "high", "description": "检测新增的 API 端点是否缺少身份验证/授权注解。所有新 API 应确保有权限控制。", "detection": "static", "bad_code": "@app.post(\"/admin/delete\")\ndef delete_user():  # no auth!", "good_code": "@app.post(\"/admin/delete\")\n@require_auth\ndef delete_user():"},
        {"id": "S009", "name": "missing_validation", "severity": "medium", "description": "检测新增 API 端点是否缺少参数校验注解（@Valid、@NotNull 等）。", "detection": "static", "bad_code": "@app.post(\"/user\")\ndef create_user(name: str):  # no validation", "good_code": "@app.post(\"/user\")\ndef create_user(@NotBlank name: str):"},
        {"id": "S010", "name": "broad_exception", "severity": "high", "description": "检测是否捕获了过于宽泛的异常（Exception 或 Throwable）。应捕获具体异常类型。", "detection": "static", "bad_code": "try:\n    process()\nexcept Exception:\n    pass", "good_code": "try:\n    process()\nexcept ValueError:\n    handle_value_error()"},
        {"id": "S011", "name": "loop_db_call", "severity": "high", "description": "检测循环体内是否包含数据库查询或 API 调用，可能导致 N+1 性能问题。", "detection": "static", "bad_code": "for user_id in ids:\n    user = db.query(User).get(user_id)", "good_code": "users = db.query(User).filter(User.id.in_(ids)).all()"},
        {"id": "S012", "name": "no_pagination", "severity": "medium", "description": "检测列表查询接口是否缺少分页或 LIMIT 限制。无分页的查询可能导致性能问题或 OOM。", "detection": "ai", "bad_code": "@app.get(\"/users\")\ndef list_users():\n    return db.query(User).all()", "good_code": "@app.get(\"/users\")\ndef list_users(page: int, size: int):\n    return db.query(User).offset(page).limit(size).all()"},
        {"id": "S013", "name": "transaction_risk", "severity": "high", "description": "检测一个方法内多次数据库写操作但缺少事务包裹。多步写入应放在同一事务中。", "detection": "ai", "bad_code": "def transfer():\n    db.execute(\"UPDATE account SET ...\")\n    db.execute(\"UPDATE account SET ...\")", "good_code": "def transfer():\n    with db.transaction():\n        db.execute(\"UPDATE account SET ...\")\n        db.execute(\"UPDATE account SET ...\")"},
        {"id": "S014", "name": "unsafe_delete_or_update", "severity": "critical", "description": "检测 SQL 的 DELETE/UPDATE 语句是否缺少 WHERE 条件。无条件的更新/删除可能导致数据丢失。", "detection": "static", "bad_code": "DELETE FROM users\nUPDATE account SET balance = 0", "good_code": "DELETE FROM users WHERE id = ?\nUPDATE account SET balance = 0 WHERE id = ?"},
        {"id": "S015", "name": "test_missing", "severity": "medium", "description": "核心源码文件变更但对应的测试文件未更新。建议为新增/修改的逻辑补充测试用例。", "detection": "ai", "bad_code": "Modified: src/service.py  (no test update)", "good_code": "Modified: src/service.py, tests/test_service.py"},
    ]
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
