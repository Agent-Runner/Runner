#!/usr/bin/env python3
"""
Sync fork with upstream repository.

This script syncs a fork with its upstream repository using the GitHub API.

Environment variables:
    BOT_TOKEN: GitHub PAT with repo scope
    FORK_REPO: Fork repository path (owner/repo)
    UPSTREAM_REPO: Upstream repository path (owner/repo)
"""

import os
import sys

import httpx


def get_env(name: str) -> str:
    """Get environment variable or exit with error."""
    value = os.environ.get(name)
    if not value:
        print(f"::error::Required environment variable {name} not set")
        sys.exit(1)
    return value


def set_github_env(name: str, value: str) -> None:
    github_env = os.environ.get("GITHUB_ENV")
    if not github_env:
        return
    with open(github_env, "a") as f:
        f.write(f"{name}={value}\n")


def fail(message: str) -> int:
    safe_message = " ".join(message.splitlines()).strip()
    print(f"::error::{safe_message}")
    set_github_env("WORKFLOW_ERROR", safe_message)
    return 1


def main() -> int:
    bot_token = get_env("BOT_TOKEN")
    fork_repo = get_env("FORK_REPO")
    upstream_repo = get_env("UPSTREAM_REPO")
    
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    print("::group::Syncing fork with upstream")

    try:
        # Preflight: validate upstream/fork repos are accessible before doing any work.
        with httpx.Client(timeout=30.0) as client:
            upstream_response = client.get(
                f"https://api.github.com/repos/{upstream_repo}",
                headers=headers,
            )

            if upstream_response.status_code != 200:
                return fail(
                    f"Upstream repository '{upstream_repo}' is not accessible (HTTP {upstream_response.status_code}). "
                    "It may not exist or BOT_TOKEN lacks permission."
                )

            fork_response = client.get(
                f"https://api.github.com/repos/{fork_repo}",
                headers=headers,
            )
            if fork_response.status_code != 200:
                return fail(
                    f"Fork repository '{fork_repo}' is not accessible (HTTP {fork_response.status_code}). "
                    "It may not exist or BOT_TOKEN lacks permission."
                )

            fork_info = fork_response.json() or {}
            if fork_info.get("fork") is not True:
                return fail(f"Fork repository '{fork_repo}' is not a GitHub fork; refusing to run the agent.")

            parent_full_name = (fork_info.get("parent") or {}).get("full_name")
            source_full_name = (fork_info.get("source") or {}).get("full_name")
            if upstream_repo not in {parent_full_name, source_full_name}:
                return fail(
                    f"Fork repository '{fork_repo}' is not a fork of '{upstream_repo}' "
                    f"(parent: {parent_full_name or 'n/a'}, source: {source_full_name or 'n/a'}); refusing to run the agent."
                )

            permissions = fork_info.get("permissions") or {}
            if permissions and not permissions.get("push", False):
                return fail(
                    f"BOT_TOKEN does not have push access to fork repository '{fork_repo}'; refusing to run the agent."
                )

            default_branch = (upstream_response.json() or {}).get("default_branch", "main")
            print(f"Upstream default branch: {default_branch}")

            # Sync fork with upstream using GitHub API
            response = client.post(
                f"https://api.github.com/repos/{fork_repo}/merge-upstream",
                headers=headers,
                json={"branch": default_branch},
            )

            if response.status_code == 200:
                print("✅ Fork synced with upstream successfully")
            elif response.status_code == 409:
                print("ℹ️ Fork is already up to date with upstream")
            else:
                print(f"::warning::Could not sync fork (HTTP {response.status_code}). Continuing anyway...")

        return 0
    finally:
        print("::endgroup::")


if __name__ == "__main__":
    sys.exit(main())
