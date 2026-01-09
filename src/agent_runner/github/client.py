"""
GitHub API client wrapper.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Async GitHub API client.
    
    Provides a reusable HTTP client with proper headers and error handling.
    """
    
    GITHUB_API = "https://api.github.com"
    
    def __init__(self, token: str, timeout: float = 30.0):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub Personal Access Token
            timeout: Request timeout in seconds
        """
        self.token = token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create reusable HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client. Call this when shutting down."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """Send GET request to GitHub API."""
        client = await self._get_client()
        url = f"{self.GITHUB_API}{path}" if path.startswith("/") else f"{self.GITHUB_API}/{path}"
        return await client.get(url, headers=self._headers, **kwargs)
    
    async def post(self, path: str, json: Optional[dict] = None, **kwargs) -> httpx.Response:
        """Send POST request to GitHub API."""
        client = await self._get_client()
        url = f"{self.GITHUB_API}{path}" if path.startswith("/") else f"{self.GITHUB_API}/{path}"
        return await client.post(url, headers=self._headers, json=json, **kwargs)
    
    async def get_repo(self, repo: str) -> dict:
        """
        Get repository information.
        
        Args:
            repo: Repository path (owner/repo)
            
        Returns:
            Repository data dict
            
        Raises:
            Exception: If repository not found or API error
        """
        response = await self.get(f"/repos/{repo}")
        if response.status_code != 200:
            raise Exception(f"Failed to get repo {repo}: {response.status_code} - {response.text}")
        return response.json()
    
    async def get_default_branch(self, repo: str) -> str:
        """
        Get the default branch of a repository.
        
        Args:
            repo: Repository path (owner/repo)
            
        Returns:
            Default branch name (e.g., "main")
        """
        repo_data = await self.get_repo(repo)
        return repo_data.get("default_branch", "main")
