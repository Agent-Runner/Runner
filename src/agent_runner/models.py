"""
Data models for Agent Runner.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class JobStatus(Enum):
    """Status of an agent runner job."""
    PENDING = "pending"           # Job created, not yet started
    FORKING = "forking"           # Creating fork
    FORK_READY = "fork_ready"     # Fork created and ready
    TRIGGERED = "triggered"       # Workflow triggered
    RUNNING = "running"           # Workflow running
    COMPLETED = "completed"       # Workflow completed successfully
    FAILED = "failed"             # Workflow failed
    CANCELLED = "cancelled"       # Job cancelled


@dataclass
class Job:
    """Represents a single agent runner job."""
    job_id: str
    upstream_repo: str
    prompt: str
    callback_url: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    fork_repo: Optional[str] = None
    branch: Optional[str] = None
    pr_url: Optional[str] = None
    workflow_run_id: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert job to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "upstream_repo": self.upstream_repo,
            "prompt": self.prompt,
            "callback_url": self.callback_url,
            "status": self.status.value,
            "fork_repo": self.fork_repo,
            "branch": self.branch,
            "pr_url": self.pr_url,
            "workflow_run_id": self.workflow_run_id,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def update_status(self, status: JobStatus) -> None:
        """Update job status and timestamp."""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_completed(self, pr_url: Optional[str] = None) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.pr_url = pr_url
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str) -> None:
        """Mark job as failed with error message."""
        self.status = JobStatus.FAILED
        self.error = error
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class CallbackPayload:
    """Payload for webhook callbacks."""
    job_id: str
    status: str  # completed, failed
    pr_url: Optional[str] = None
    error: Optional[str] = None
    upstream_repo: Optional[str] = None
    fork_repo: Optional[str] = None
    branch: Optional[str] = None
