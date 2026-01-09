"""
Agent Runner - AI-powered code modification runner using OpenHands SDK.

This package provides:
- Core service for managing agent runner jobs
- GitHub API integrations (fork, PR, workflow dispatch)
- CLI for GitHub Actions workflow_dispatch
- Optional HTTP server for REST API access
"""

from agent_runner.core import AgentRunner
from agent_runner.models import Job, JobStatus

__version__ = "1.0.0"
__all__ = ["AgentRunner", "Job", "JobStatus"]
