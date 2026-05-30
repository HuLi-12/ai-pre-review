import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, DECIMAL, ForeignKey
from app.database import Base


class PRReviewTask(Base):
    __tablename__ = "pr_review_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_owner = Column(String(128), nullable=False)
    repo_name = Column(String(128), nullable=False)
    pr_number = Column(Integer, nullable=False)
    pr_url = Column(String(512), nullable=False)
    commit_sha = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="PENDING")
    auto_comment = Column(Integer, default=0)
    comment_id = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    risk_level = Column(String(32), nullable=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    raw_finding_count = Column(Integer, default=0)
    deduped_finding_count = Column(Integer, default=0)
    visible_finding_count = Column(Integer, default=0)
    github_ready_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PRChangedFile(Base):
    __tablename__ = "pr_changed_file"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("pr_review_task.id"), nullable=False)
    file_path = Column(String(512), nullable=False)
    change_type = Column(String(32), nullable=True)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    patch = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    risk_level = Column(String(32), nullable=True)
    risk_score = Column(Integer, default=0)
    file_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PRReviewFinding(Base):
    __tablename__ = "pr_review_finding"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("pr_review_task.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("pr_changed_file.id"), nullable=True)
    file_path = Column(String(512), nullable=True)
    line_number = Column(Integer, nullable=True)
    finding_type = Column(String(64), nullable=True)
    severity = Column(String(32), nullable=True)
    title = Column(String(512), nullable=True)
    reason = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    confidence = Column(DECIMAL(4, 3), nullable=True)
    evidence_json = Column(Text, nullable=True)
    status = Column(String(32), default="OPEN")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PRReviewFeedback(Base):
    __tablename__ = "pr_review_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    finding_id = Column(Integer, ForeignKey("pr_review_finding.id"), nullable=False)
    feedback_type = Column(String(32), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
