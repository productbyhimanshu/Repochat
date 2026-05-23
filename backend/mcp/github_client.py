"""
github_client.py — GitHub REST API client.

All GitHub calls go through this module. Results are cached to session_store immediately.
The mcp stdlib package is not required; we use httpx directly against the GitHub v3 REST API.
"""

import os
import base64
import httpx

from session import require_session
from logger import get_logger

log = get_logger("repochat.mcp.github")

_BASE = "https://api.github.com"
_TOKEN_VALID: bool | None = None  # None = untested, True = works, False = invalid


def _headers(authenticated: bool = True) -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if authenticated:
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            h["Authorization"] = f"Bearer {token}"
    return h


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """GET with automatic fallback to unauthenticated on 401. Raises on 403 rate limit."""
    global _TOKEN_VALID
    headers = kwargs.pop("headers", _headers(authenticated=True))
    res = await client.get(url, headers=headers, **kwargs)
    if res.status_code == 401 and "Authorization" in headers:
        log.warning("GitHub token invalid or expired — falling back to unauthenticated (update GITHUB_TOKEN in .env)")
        _TOKEN_VALID = False
        res = await client.get(url, headers=_headers(authenticated=False), **kwargs)
    if res.status_code == 403:
        remaining = res.headers.get("X-RateLimit-Remaining", "?")
        raise RuntimeError(
            f"GitHub API rate limit exceeded (remaining={remaining}). "
            "Set a valid GITHUB_TOKEN in .env to get 5000 req/hour instead of 60."
        )
    return res


def _get_cache(session_id: str) -> dict:
    store = require_session(session_id)
    if "mcp_cache" not in store:
        store["mcp_cache"] = {}
    return store["mcp_cache"]


# ── 5 GitHub client functions ──────────────────────────────────────────────────

async def get_file_tree(session_id: str, owner: str, repo: str) -> list:
    """Return list of all blob paths in the repo (recursive)."""
    cache = _get_cache(session_id)
    cache_key = f"tree:{owner}/{repo}"

    if cache_key in cache:
        log.cache(hit=True, key=cache_key)
        return cache[cache_key]

    log.cache(hit=False, key=cache_key)
    log.agent("github_client", f"Fetching file tree for {owner}/{repo}")

    async with httpx.AsyncClient(timeout=30) as client:
        repo_res = await _get(client, f"{_BASE}/repos/{owner}/{repo}")
        repo_res.raise_for_status()
        default_branch = repo_res.json().get("default_branch", "main")

        tree_res = await _get(
            client,
            f"{_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
        )
        tree_res.raise_for_status()
        files = [
            item["path"]
            for item in tree_res.json().get("tree", [])
            if item["type"] == "blob"
        ]

    cache[cache_key] = files
    return files


async def get_file_contents(session_id: str, owner: str, repo: str, path: str) -> str:
    """Return raw string content of a file. Returns '' on 404."""
    cache = _get_cache(session_id)
    cache_key = f"file:{owner}/{repo}:{path}"

    if cache_key in cache:
        log.cache(hit=True, key=cache_key)
        return cache[cache_key]

    log.cache(hit=False, key=cache_key)
    log.agent("github_client", f"Fetching {path}")

    async with httpx.AsyncClient(timeout=30) as client:
        res = await _get(client, f"{_BASE}/repos/{owner}/{repo}/contents/{path}")
        if res.status_code == 404:
            cache[cache_key] = ""
            return ""
        res.raise_for_status()
        data = res.json()

    if isinstance(data, dict) and data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    else:
        content = str(data)

    cache[cache_key] = content
    return content


async def search_code(session_id: str, owner: str, repo: str, query: str) -> dict:
    """Search code in repo for a keyword (e.g. TODO, FIXME)."""
    cache = _get_cache(session_id)
    cache_key = f"search:{owner}/{repo}:{query}"

    if cache_key in cache:
        log.cache(hit=True, key=cache_key)
        return cache[cache_key]

    log.cache(hit=False, key=cache_key)
    log.agent("github_client", f"Searching code for '{query}' in {owner}/{repo}")

    async with httpx.AsyncClient(timeout=30) as client:
        res = await _get(
            client,
            f"{_BASE}/search/code",
            params={"q": f"repo:{owner}/{repo} {query}", "per_page": 10},
            headers={**_headers(), "Accept": "application/vnd.github.v3.text-match+json"},
        )
        if res.status_code in (422, 403, 451, 401):
            result: dict = {"items": [], "total_count": 0}
        else:
            res.raise_for_status()
            result = res.json()

    cache[cache_key] = result
    return result


async def list_commits(session_id: str, owner: str, repo: str, limit: int = 30) -> list:
    """Return list of recent commits (up to `limit`)."""
    cache = _get_cache(session_id)
    cache_key = f"commits:{owner}/{repo}:{limit}"

    if cache_key in cache:
        log.cache(hit=True, key=cache_key)
        return cache[cache_key]

    log.cache(hit=False, key=cache_key)
    log.agent("github_client", f"Listing commits for {owner}/{repo}")

    async with httpx.AsyncClient(timeout=30) as client:
        res = await _get(
            client,
            f"{_BASE}/repos/{owner}/{repo}/commits",
            params={"per_page": min(limit, 100)},
        )
        res.raise_for_status()
        commits = res.json()

    result = commits[:limit] if isinstance(commits, list) else []
    cache[cache_key] = result
    return result


async def list_issues(
    session_id: str, owner: str, repo: str, state: str = "open", limit: int = 20
) -> list:
    """Return list of issues."""
    cache = _get_cache(session_id)
    cache_key = f"issues:{owner}/{repo}:{state}:{limit}"

    if cache_key in cache:
        log.cache(hit=True, key=cache_key)
        return cache[cache_key]

    log.cache(hit=False, key=cache_key)
    log.agent("github_client", f"Listing {state} issues for {owner}/{repo}")

    async with httpx.AsyncClient(timeout=30) as client:
        res = await _get(
            client,
            f"{_BASE}/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": min(limit, 100)},
        )
        res.raise_for_status()
        issues = res.json()

    result = issues[:limit] if isinstance(issues, list) else []
    cache[cache_key] = result
    return result
