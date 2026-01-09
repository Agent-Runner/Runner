"""
GitHub repository operations (fork, sync, clone).
"""

import asyncio
import logging
import time
from typing import Optional

from agent_runner.github.client import GitHubClient

logger = logging.getLogger(__name__)


class RepoManager:
    """
    Manages GitHub repository operations.
    
    Handles:
    - Creating/getting forks
    - Syncing forks with upstream
    - Waiting for fork to be ready
    """
    
    def __init__(
        self,
        client: GitHubClient,
        bot_username: str,
        fork_timeout: int = 120,
        fork_poll_interval: int = 5,
    ):
        """
        Initialize repository manager.
        
        Args:
            client: GitHub API client
            bot_username: GitHub username of the bot account
            fork_timeout: Maximum seconds to wait for fork to be ready
            fork_poll_interval: Seconds between fork status checks
        """
        self.client = client
        self.bot_username = bot_username
        self.fork_timeout = fork_timeout
        self.fork_poll_interval = fork_poll_interval
    
    async def create_or_get_fork(self, upstream_repo: str) -> str:
        """
        Create a fork or return existing fork.
        
        Args:
            upstream_repo: Repository to fork (e.g., "owner/repo")
            
        Returns:
            Fork repository path (e.g., "bot-username/repo")
            
        Raises:
            ValueError: If upstream_repo format is invalid or naming conflict
            Exception: If fork creation fails
        """
        parts = upstream_repo.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid upstream_repo format: {upstream_repo}")
        
        repo_name = parts[1]
        fork_repo = f"{self.bot_username}/{repo_name}"
        
        # Check if fork already exists
        response = await self.client.get(f"/repos/{fork_repo}")
        
        if response.status_code == 200:
            fork_data = response.json()
            # Verify it's actually a fork of the upstream
            if fork_data.get("fork") and fork_data.get("parent", {}).get("full_name") == upstream_repo:
                logger.info(f"Using existing fork: {fork_repo}")
                # Sync fork with upstream
                await self.sync_fork(fork_repo, upstream_repo)
                return fork_repo
            else:
                # Repo exists but is not a fork of upstream - naming conflict
                raise ValueError(
                    f"Repository {fork_repo} exists but is not a fork of {upstream_repo}. "
                    "Please rename or delete the conflicting repository."
                )
        
        # Create new fork
        logger.info(f"Creating fork of {upstream_repo}...")
        response = await self.client.post(
            f"/repos/{upstream_repo}/forks",
            json={"default_branch_only": True},
        )
        
        if response.status_code not in (202, 200):
            raise Exception(f"Failed to create fork: {response.status_code} - {response.text}")
        
        # Wait for fork to be ready
        await self.wait_for_fork(fork_repo)
        
        return fork_repo
    
    async def wait_for_fork(self, fork_repo: str) -> None:
        """
        Wait for a fork to be ready (cloneable).
        
        Args:
            fork_repo: Fork repository path
            
        Raises:
            TimeoutError: If fork doesn't become ready within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.fork_timeout:
            response = await self.client.get(f"/repos/{fork_repo}")
            
            if response.status_code == 200:
                # Try to verify the repo is actually ready by checking branches
                branches_response = await self.client.get(f"/repos/{fork_repo}/branches")
                if branches_response.status_code == 200 and branches_response.json():
                    logger.info(f"Fork {fork_repo} is ready!")
                    return
            
            logger.debug(f"Waiting for fork {fork_repo} to be ready...")
            await asyncio.sleep(self.fork_poll_interval)
        
        raise TimeoutError(f"Fork {fork_repo} did not become ready within {self.fork_timeout} seconds")
    
    async def sync_fork(self, fork_repo: str, upstream_repo: str) -> bool:
        """
        Sync fork with upstream (fetch latest changes).
        
        Args:
            fork_repo: Fork repository path
            upstream_repo: Upstream repository path
            
        Returns:
            True if sync was successful, False otherwise
        """
        # Get upstream default branch
        try:
            default_branch = await self.client.get_default_branch(upstream_repo)
        except Exception:
            logger.warning("Could not get upstream info for sync")
            return False
        
        # Sync fork using GitHub's merge-upstream API
        response = await self.client.post(
            f"/repos/{fork_repo}/merge-upstream",
            json={"branch": default_branch},
        )
        
        if response.status_code == 200:
            logger.info(f"Fork {fork_repo} synced with upstream")
            return True
        elif response.status_code == 409:
            logger.debug(f"Fork {fork_repo} already up to date")
            return True
        else:
            logger.warning(f"Could not sync fork: {response.status_code}")
            return False
    
    def get_fork_repo_name(self, upstream_repo: str) -> str:
        """
        Get the expected fork repository path.
        
        Args:
            upstream_repo: Upstream repository path (owner/repo)
            
        Returns:
            Fork repository path (bot-username/repo)
        """
        parts = upstream_repo.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid upstream_repo format: {upstream_repo}")
        return f"{self.bot_username}/{parts[1]}"
