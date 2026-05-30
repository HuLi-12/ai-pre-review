from dataclasses import asdict

from fastapi import APIRouter

from app.golden_evaluation import run_golden_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/golden")
def get_golden_evaluation():
    """Run deterministic golden review evaluation cases."""
    return asdict(run_golden_evaluation())
