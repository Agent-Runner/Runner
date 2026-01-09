"""
GitHub Pull Request operations.
"""

import logging

from agent_runner.github.client import GitHubClient

logger = logging.getLogger(__name__)


class PRManager:
    """
    Manages GitHub Pull Request operations.
    
    Handles:
    - Creating pull requests
    - Finding existing PRs
    """
    
    def __init__(self, client: GitHubClient):
        """
        Initialize PR manager.
        
        Args:
            client: GitHub API client
        """
        self.client = client
    
    async def create_pr(
        self,
        upstream_repo: str,
        fork_repo: str,
        branch: str,
        title: str,
        body: str,
    ) -> str:
        """
        Create a pull request from fork to upstream.
        
        Args:
            upstream_repo: Target repository (e.g., "owner/repo")
            fork_repo: Source fork repository
            branch: Branch name in the fork
            title: PR title
            body: PR body/description
            
        Returns:
            Pull request URL
            
        Raises:
            Exception: If PR creation fails
        """
        # Get upstream default branch
        base = await self.client.get_default_branch(upstream_repo)
        
        # Head must be "<fork_owner>:<branch>"
        fork_owner = fork_repo.split("/")[0]
        head = f"{fork_owner}:{branch}"
        
        response = await self.client.post(
            f"/repos/{upstream_repo}/pulls",
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
            },
        )
        
        if response.status_code == 201:
            pr_url = response.json().get("html_url", "")
            logger.info(f"PR created: {pr_url}")
            return pr_url
        
        # Check if PR already exists
        data = response.json()
        message = data.get("message", "")
        errors = data.get("errors", [])
        error_messages = " ".join(e.get("message", "") for e in errors)
        
        if "already exists" in message.lower() or "already exists" in error_messages.lower():
            logger.warning(f"PR already exists for head '{head}'; fetching existing PR URL.")
            return await self.find_existing_pr(upstream_repo, head)
        
        raise Exception(f"Failed to create PR: {response.status_code} - {response.text}")
    
    async def find_existing_pr(
        self,
        upstream_repo: str,
        head: str,
        state: str = "open",
    ) -> str:
        """
        Find an existing pull request.
        
        Args:
            upstream_repo: Target repository
            head: Head reference (owner:branch)
            state: PR state filter (open, closed, all)
            
        Returns:
            Pull request URL
            
        Raises:
            Exception: If no PR found
        """
        response = await self.client.get(
            f"/repos/{upstream_repo}/pulls",
            params={
                "head": head,
                "state": state,
                "per_page": 1,
            },
        )
        
        if response.status_code == 200:
            prs = response.json()
            if prs:
                return prs[0].get("html_url", "")
        
        raise Exception(f"No existing PR found for head '{head}'")
