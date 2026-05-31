from app.models import PRReviewTask
from app.routers.tasks import _mark_task_done


def test_mark_task_done_preserves_dry_run_step():
    task = PRReviewTask(
        repo_owner="demo",
        repo_name="repo",
        pr_number=1,
        pr_url="https://github.com/demo/repo/pull/1",
        status="DRY_RUN",
        current_step="DRY_RUN",
    )

    _mark_task_done(task)

    assert task.status == "DONE"
    assert task.progress == 100
    assert task.current_step == "DRY_RUN"


def test_mark_task_done_preserves_comment_result_step():
    task = PRReviewTask(
        repo_owner="demo",
        repo_name="repo",
        pr_number=1,
        pr_url="https://github.com/demo/repo/pull/1",
        status="COMMENTED",
        current_step="COMMENT_UPDATED",
    )

    _mark_task_done(task)

    assert task.status == "DONE"
    assert task.current_step == "COMMENT_UPDATED"


def test_mark_task_done_defaults_to_completed_for_normal_review():
    task = PRReviewTask(
        repo_owner="demo",
        repo_name="repo",
        pr_number=1,
        pr_url="https://github.com/demo/repo/pull/1",
        status="GENERATING_REPORT",
        current_step="GENERATING_REPORT",
    )

    _mark_task_done(task)

    assert task.status == "DONE"
    assert task.current_step == "COMPLETED"
