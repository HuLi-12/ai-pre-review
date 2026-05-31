from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class CreateTaskRequest(BaseModel):
    pr_url: str = Field(..., description="GitHub PR URL")
    github_token: Optional[str] = Field(None, description="GitHub Token, 不传则使用全局配置")
    auto_comment: bool = Field(False, description="是否自动评论到 GitHub")
    dry_run: bool = Field(False, description="安全预览模式，不实际发布到 GitHub")


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    status: str
    progress: Optional[int] = 0
    current_step: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    fallback_flags: Optional[str] = None
    pipeline_details: Optional[str] = None


class FindingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    summary: Optional[str] = None
    risk_level: Optional[str] = None
    merge_suggestion: Optional[str] = None
    findings: List[FindingItem] = []
    test_suggestions: List[str] = []
    key_focus_points: List[str] = []
    raw_finding_count: int = 0
    deduped_finding_count: int = 0
    visible_finding_count: int = 0
    github_ready_count: int = 0
    invalid_finding_count: int = 0


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="FALSE_POSITIVE / EFFECTIVE / RESOLVED")
    comment: Optional[str] = None
