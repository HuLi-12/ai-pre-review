from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateTaskRequest(BaseModel):
    pr_url: str = Field(..., description="GitHub PR URL")
    github_token: Optional[str] = Field(None, description="GitHub Token, 不传则使用全局配置")
    auto_comment: bool = Field(False, description="是否自动评论到 GitHub")


class TaskResponse(BaseModel):
    task_id: int
    status: str
    progress: Optional[int] = 0
    current_step: Optional[str] = None

    class Config:
        from_attributes = True


class FindingItem(BaseModel):
    id: int
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    finding_type: Optional[str] = None
    severity: str
    title: str
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    confidence: Optional[float] = None
    evidence_json: Optional[str] = None

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    task_id: int
    summary: Optional[str] = None
    risk_level: Optional[str] = None
    merge_suggestion: Optional[str] = None
    findings: List[FindingItem] = []
    test_suggestions: List[str] = []
    key_focus_points: List[str] = []

    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="FALSE_POSITIVE / EFFECTIVE / RESOLVED")
    comment: Optional[str] = None
