"""
Webhook callback handling.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class CallbackHandler:
    """
    Handles webhook callback operations.
    
    Provides:
    - Sending callback notifications
    - Generating HMAC signatures
    - Verifying webhook signatures
    """
    
    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        allow_insecure: bool = False,
    ):
        """
        Initialize callback handler.
        
        Args:
            webhook_secret: Secret for HMAC signature
            allow_insecure: Allow unsigned webhooks (NOT recommended for production)
        """
        self.webhook_secret = webhook_secret
        self.allow_insecure = allow_insecure
    
    def generate_signature(self, payload: bytes) -> str:
        """
        Generate HMAC-SHA256 signature for payload.
        
        Args:
            payload: Raw payload bytes
            
        Returns:
            Signature string in format "sha256=<hex>"
        """
        if not self.webhook_secret:
            return ""
        
        return "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.
        
        Args:
            payload: Raw request body
            signature: X-Signature-256 header value
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            if self.allow_insecure:
                logger.warning("No webhook_secret configured - signature verification skipped")
                return True
            logger.error("No webhook_secret configured - rejecting webhook")
            return False
        
        expected = self.generate_signature(payload)
        return hmac.compare_digest(expected, signature)
    
    async def send_callback(
        self,
        callback_url: str,
        payload: dict,
        timeout: float = 10.0,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
    ) -> bool:
        """
        Send callback notification to URL.
        
        Args:
            callback_url: URL to POST to
            payload: JSON payload
            timeout: Request timeout in seconds
            max_attempts: Maximum number of attempts to send callback
            backoff_seconds: Base backoff delay between retries in seconds
            
        Returns:
            True if callback was sent successfully
        """
        if not callback_url:
            logger.debug("No callback URL configured, skipping")
            return False
        
        payload_bytes = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}

        if self.webhook_secret:
            signature = self.generate_signature(payload_bytes)
            headers["X-Signature-256"] = signature

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = await client.post(
                        callback_url,
                        content=payload_bytes,
                        headers=headers,
                    )

                    if response.status_code < 400:
                        logger.info(f"Callback sent to {callback_url}")
                        return True

                    response_snippet = response.text[:200] if response.text else ""
                    log_suffix = f": {response_snippet}" if response_snippet else ""
                    if response.status_code == 429 or response.status_code >= 500:
                        logger.warning(
                            "Callback attempt %s failed with status %s%s",
                            attempt,
                            response.status_code,
                            log_suffix,
                        )
                    else:
                        logger.warning(
                            "Callback failed with status %s%s",
                            response.status_code,
                            log_suffix,
                        )
                        return False
                except httpx.RequestError as e:
                    logger.warning("Callback attempt %s failed: %s", attempt, e)
                except Exception as e:
                    logger.error(f"Failed to send callback: {e}")
                    return False

                if attempt < max_attempts:
                    await asyncio.sleep(backoff_seconds * attempt)

        return False
    
    async def send_success_callback(
        self,
        callback_url: str,
        job_id: str,
        pr_url: Optional[str],
        upstream_repo: str,
        fork_repo: str,
        branch: str,
    ) -> bool:
        """
        Send success callback notification.
        
        Args:
            callback_url: URL to POST to
            job_id: Job identifier
            pr_url: Pull request URL (if created)
            upstream_repo: Upstream repository
            fork_repo: Fork repository
            branch: Branch name
            
        Returns:
            True if callback sent successfully
        """
        payload = {
            "job_id": job_id,
            "status": "completed",
            "pr_url": pr_url,
            "upstream_repo": upstream_repo,
            "fork_repo": fork_repo,
            "branch": branch,
        }
        return await self.send_callback(callback_url, payload)
    
    async def send_failure_callback(
        self,
        callback_url: str,
        job_id: str,
        error: str,
        upstream_repo: str,
        fork_repo: Optional[str] = None,
    ) -> bool:
        """
        Send failure callback notification.
        
        Args:
            callback_url: URL to POST to
            job_id: Job identifier
            error: Error message
            upstream_repo: Upstream repository
            fork_repo: Fork repository (if available)
            
        Returns:
            True if callback sent successfully
        """
        payload = {
            "job_id": job_id,
            "status": "failed",
            "error": error,
            "upstream_repo": upstream_repo,
            "fork_repo": fork_repo,
        }
        return await self.send_callback(callback_url, payload)
