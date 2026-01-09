"""
GitHub Workflow dispatch operations.
"""

import logging
from typing import Optional

from agent_runner.github.client import GitHubClient
from agent_runner.models import Job

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Manages GitHub Actions workflow operations.
    
    Handles:
    - Triggering workflows via dispatch
    """
    
    def __init__(self, client: GitHubClient, runner_repo: str):
        """
        Initialize workflow manager.
        
        Args:
            client: GitHub API client
            runner_repo: Repository containing the workflow
        """
        self.client = client
        self.runner_repo = runner_repo
    
    async def trigger_workflow(
        self,
        job: Job,
        workflow_file: str = "run.yml",
        ref: str = "main",
    ) -> None:
        """
        Trigger the Agent-Runner workflow.
        
        Args:
            job: Job to run
            workflow_file: Workflow filename
            ref: Git ref to run workflow on
            
        Raises:
            Exception: If workflow dispatch fails
        """
        response = await self.client.post(
            f"/repos/{self.runner_repo}/actions/workflows/{workflow_file}/dispatches",
            json={
                "ref": ref,
                "inputs": {
                    "fork_repo": job.fork_repo or "",
                    "upstream_repo": job.upstream_repo,
                    "prompt": job.prompt,
                    "job_id": job.job_id,
                    "callback_url": job.callback_url or "",
                },
            },
        )
        
        if response.status_code != 204:
            raise Exception(f"Failed to trigger workflow: {response.status_code} - {response.text}")
        
        logger.info(f"Workflow triggered for job {job.job_id}")
    
    async def dispatch(
        self,
        fork_repo: str,
        upstream_repo: str,
        prompt: str,
        job_id: str,
        callback_url: Optional[str] = None,
        workflow_file: str = "run.yml",
        ref: str = "main",
    ) -> None:
        """
        Dispatch a workflow with raw parameters.
        
        This is a lower-level method for direct workflow dispatch.
        
        Args:
            fork_repo: Fork repository path
            upstream_repo: Upstream repository path
            prompt: Agent prompt
            job_id: Job identifier
            callback_url: Optional callback URL
            workflow_file: Workflow filename
            ref: Git ref to run workflow on
        """
        response = await self.client.post(
            f"/repos/{self.runner_repo}/actions/workflows/{workflow_file}/dispatches",
            json={
                "ref": ref,
                "inputs": {
                    "fork_repo": fork_repo,
                    "upstream_repo": upstream_repo,
                    "prompt": prompt,
                    "job_id": job_id,
                    "callback_url": callback_url or "",
                },
            },
        )
        
        if response.status_code != 204:
            raise Exception(f"Failed to trigger workflow: {response.status_code} - {response.text}")
        
        logger.info(f"Workflow dispatched for job {job_id}")
