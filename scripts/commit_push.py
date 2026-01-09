#!/usr/bin/env python3
"""
Commit and push changes to the fork repository.

This script:
1. Stages and commits any uncommitted changes
2. Checks if there are commits ahead of upstream
3. Pushes the branch (with force-push fallback)
4. Sets HAS_CHANGES and PR_URL environment variables for subsequent steps

Environment variables:
    BOT_TOKEN: GitHub PAT with repo scope
    FORK_REPO: Fork repository path (owner/repo)
    UPSTREAM_REPO: Upstream repository path (owner/repo)
    AGENT_PROMPT: The prompt used (for commit message)
    JOB_ID: Job identifier
"""

import os
import subprocess
import sys
from typing import Optional


def run_cmd(cmd: list[str], cwd: str = "repo", check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        print(f"::error::Command failed: {' '.join(cmd)}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(result.returncode)
    return result


def set_github_env(name: str, value: str) -> None:
    """Set GitHub Actions environment variable for subsequent steps."""
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"export {name}={value}")


def get_remote_default_branch(remote: str) -> str:
    """Best-effort detection of a git remote's default branch."""
    result = run_cmd(["git", "symbolic-ref", f"refs/remotes/{remote}/HEAD"], check=False)
    if result.returncode == 0:
        return result.stdout.strip().split("/")[-1]

    result = run_cmd(["git", "remote", "show", remote], check=False)
    for line in result.stdout.split("\n"):
        if "HEAD branch" in line:
            return line.split()[-1]

    return "main"


def main() -> int:
    bot_token = os.environ.get("BOT_TOKEN", "")
    fork_repo = os.environ.get("FORK_REPO", "")
    upstream_repo = os.environ.get("UPSTREAM_REPO", "")
    prompt = os.environ.get("AGENT_PROMPT", "")
    
    # Configure git
    run_cmd(["git", "config", "user.name", "agent-bot"])
    run_cmd(["git", "config", "user.email", "agent-bot@users.noreply.github.com"])
    
    # Debug: Show current status
    print("::group::Git Status")
    run_cmd(["git", "status"], check=False)
    print("::endgroup::")
    
    # Step 1: Stage and commit any uncommitted changes
    run_cmd(["git", "add", "-A"])
    
    # Check if there are staged changes
    diff_result = run_cmd(["git", "diff", "--cached", "--quiet"], check=False)
    
    if diff_result.returncode != 0:
        # There are staged changes, commit them
        commit_msg = f"bot: {prompt[:60]}"
        run_cmd(["git", "commit", "-m", commit_msg])
        print("✅ Committed local changes.")
    else:
        print("⚠️ No uncommitted changes to stage.")
    
    # Step 2: Check if we have commits that differ from upstream's default branch
    commits_ahead: Optional[str] = None
    base_ref: Optional[str] = None

    if upstream_repo:
        # Add upstream remote (use BOT_TOKEN so private upstreams are readable)
        upstream_url = f"https://github.com/{upstream_repo}.git"
        if bot_token:
            upstream_url = f"https://x-access-token:{bot_token}@github.com/{upstream_repo}.git"

        run_cmd(["git", "remote", "add", "upstream", upstream_url], check=False)
        if bot_token:
            run_cmd(["git", "remote", "set-url", "upstream", upstream_url], check=False)

        fetch_result = run_cmd(["git", "fetch", "upstream", "--quiet"], check=False)
        if fetch_result.returncode == 0:
            upstream_default = get_remote_default_branch("upstream")
            print(f"Upstream default branch: {upstream_default}")
            base_ref = f"upstream/{upstream_default}"
            result = run_cmd(["git", "rev-list", "--count", f"{base_ref}..HEAD"], check=False)
            if result.returncode == 0:
                commits_ahead = result.stdout.strip()
            else:
                print(f"::warning::Failed to compare against {base_ref}; falling back to origin.")
        else:
            print("::warning::Failed to fetch upstream; falling back to origin for change detection.")

    if commits_ahead is None:
        origin_default = get_remote_default_branch("origin")
        base_ref = f"origin/{origin_default}"
        result = run_cmd(["git", "rev-list", "--count", f"{base_ref}..HEAD"], check=False)
        if result.returncode != 0:
            print(f"::error::Failed to determine commits ahead of {base_ref}.")
            print(result.stderr)
            return 1
        commits_ahead = result.stdout.strip()

    print(f"Commits ahead of {base_ref}: {commits_ahead}")
    
    if commits_ahead == "0":
        print(f"⚠️ No new commits compared to {base_ref}. Nothing to PR.")
        set_github_env("HAS_CHANGES", "false")
        set_github_env("PR_URL", "")
        return 0
    
    print(f"✅ Found {commits_ahead} commit(s) to push.")
    
    # Step 3: Configure remote URL with token
    print("::group::Configuring remote with authentication")
    run_cmd(["git", "remote", "set-url", "origin", f"https://x-access-token:{bot_token}@github.com/{fork_repo}.git"])
    print("Remote URL configured (token hidden)")
    print("::endgroup::")
    
    # Step 4: Push the branch
    set_github_env("HAS_CHANGES", "true")
    
    # Get current branch name
    result = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = result.stdout.strip()
    
    print(f"::group::Pushing to origin/{branch}")
    
    # Try normal push first
    result = run_cmd(["git", "push", "-u", "origin", branch], check=False)
    
    if result.returncode == 0:
        print("✅ Push successful!")
    else:
        print(f"Push failed: {result.stderr}")
        print("::warning::Normal push failed, trying force push...")
        
        # Force push fallback
        result = run_cmd(["git", "push", "-u", "origin", branch, "--force-with-lease"], check=False)
        
        if result.returncode == 0:
            print("✅ Force push successful!")
        else:
            print(f"::error::Push failed even with force-with-lease: {result.stderr}")
            return 1
    
    print("::endgroup::")
    return 0


if __name__ == "__main__":
    sys.exit(main())
