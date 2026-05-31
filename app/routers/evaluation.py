from dataclasses import asdict

from fastapi import APIRouter

from app.golden_evaluation import run_golden_evaluation, run_real_pr_replay_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/golden")
def get_golden_evaluation():
    """Run deterministic golden review evaluation cases."""
    return asdict(run_golden_evaluation())


@router.get("/real-pr-replay")
def get_real_pr_replay_evaluation():
    """Run fixed public PR replay evaluation snapshots."""
    return asdict(run_real_pr_replay_evaluation())
