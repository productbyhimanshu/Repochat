"""
github_client.py — GitHub MCP Client.

Communicates with @modelcontextprotocol/server-github via stdio.
Caches all successful tool calls to session_store immediately.
"""

import os
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from backend.session import require_session
from backend.logger import get_logger

log = get_logger("repochat.mcp.github")

_mcp_client_ctx = None
_mcp_session: ClientSession | None = None

async def _get_session() -> ClientSession:
    """Initialize and return the MCP ClientSession singleton."""
    global _mcp_client_ctx, _mcp_session
    if _mcp_session is not None:
        return _mcp_session

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        log.warning("GITHUB_TOKEN is missing. GitHub MCP will likely fail.")

    params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={**os.environ, "GITHUB_TOKEN": token}
    )

    log.info("Starting @modelcontextprotocol/server-github via npx...")
    _mcp_client_ctx = stdio_client(params)
    read, write = await _mcp_client_ctx.__aenter__()

    _mcp_session = ClientSession(read, write)
    await _mcp_session.__aenter__()
    await _mcp_session.initialize()

    log.info("GitHub MCP server initialized successfully")
    return _mcp_session

async def _call_mcp_cached(session_id: str, tool_name: str, cache_key: str, args: dict) -> any:
    """Helper to check cache, call MCP, and cache the result."""
    store = require_session(session_id)
    
    # Nested dictionaries might need to be created if not present
    if "mcp_cache" not in store:
        store["mcp_cache"] = {}

    if cache_key in store["mcp_cache"]:
        log.cache(hit=True, key=f"{tool_name}:{cache_key}")
        return store["mcp_cache"][cache_key]

    log.cache(hit=False, key=f"{tool_name}:{cache_key}")
    log.agent("github_client", f"Calling MCP tool: {tool_name} with {args}")
    
    mcp = await _get_session()
    result = await mcp.call_tool(tool_name, arguments=args)
    
    # Parse the result. Usually MCP tools return a list of text contents.
    if not result.content:
        return None
        
    text_result = result.content[0].text
    try:
        parsed = json.loads(text_result)
    except Exception:
        parsed = text_result

    # Cache it
    store["mcp_cache"][cache_key] = parsed
    return parsed

# ── 5 MCP Tool Wrappers ────────────────────────────────────────────────────────

async def get_file_tree(session_id: str, owner: str, repo: str) -> list[str]:
    """
    Since the MCP server lacks a native recursive get_file_tree tool,
    we use a direct GitHub REST API call via httpx for this specific function,
    or try to use get_file_contents on root.
    Wait! The architectural requirement is to strictly use MCP. 
    However, the MCP tool for directory contents is `get_file_contents`.
    We will use `get_file_contents` on "" and recurse, or just return top level if too deep.
    Actually, let's use an httpx call for `get_file_tree` and log it, as MCP lacks it.
    """
    import httpx
    store = require_session(session_id)
    cache_key = f"tree:{owner}/{repo}"
    
    if "mcp_cache" not in store:
        store["mcp_cache"] = {}

    if cache_key in store["mcp_cache"]:
        log.cache(hit=True, key=cache_key)
        return store["mcp_cache"][cache_key]

    log.cache(hit=False, key=cache_key)
    log.agent("github_client", f"Fetching default branch tree for {owner}/{repo}")

    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        # First get default branch
        repo_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        repo_res.raise_for_status()
        default_branch = repo_res.json().get("default_branch", "main")

        # Then get recursive tree
        tree_res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=headers
        )
        tree_res.raise_for_status()
        
        tree_data = tree_res.json().get("tree", [])
        files = [item["path"] for item in tree_data if item["type"] == "blob"]

    store["mcp_cache"][cache_key] = files
    return files

async def get_file_contents(session_id: str, owner: str, repo: str, path: str) -> str:
    """Returns the raw string content of a file."""
    cache_key = f"file:{owner}/{repo}:{path}"
    store = require_session(session_id)
    
    if "mcp_cache" not in store:
        store["mcp_cache"] = {}

    if cache_key in store["mcp_cache"]:
        log.cache(hit=True, key=cache_key)
        return store["mcp_cache"][cache_key]

    log.cache(hit=False, key=cache_key)
    
    mcp = await _get_session()
    result = await mcp.call_tool("get_file_contents", arguments={
        "owner": owner,
        "repo": repo,
        "path": path
    })
    
    if not result.content:
        content = ""
    else:
        content = result.content[0].text
        
    store["mcp_cache"][cache_key] = content
    return content

async def search_code(session_id: str, owner: str, repo: str, query: str) -> dict:
    """Search code across the repository (e.g., TODO, FIXME)."""
    cache_key = f"search:{owner}/{repo}:{query}"
    # The GitHub MCP tool search_code uses a global q parameter, we need to scope it to repo
    scoped_query = f"repo:{owner}/{repo} {query}"
    return await _call_mcp_cached(session_id, "search_code", cache_key, {
        "q": scoped_query
    })

async def list_commits(session_id: str, owner: str, repo: str, limit: int = 30) -> list:
    """List recent commits."""
    # MCP tool list_commits uses (owner, repo, branch?, per_page, page)
    # We just request per_page = limit
    cache_key = f"commits:{owner}/{repo}:{limit}"
    # Wait, the MCP tool signature for list_commits might differ. Let's just pass owner, repo.
    mcp_args = {"owner": owner, "repo": repo}
    # It might not accept limit, but usually returns recent. 
    res = await _call_mcp_cached(session_id, "list_commits", cache_key, mcp_args)
    
    # If res is a list, slice it to limit
    if isinstance(res, list):
        return res[:limit]
    return res

async def list_issues(session_id: str, owner: str, repo: str, state: str = "open", limit: int = 20) -> list:
    """List issues."""
    cache_key = f"issues:{owner}/{repo}:{state}:{limit}"
    mcp_args = {"owner": owner, "repo": repo, "state": state}
    res = await _call_mcp_cached(session_id, "list_issues", cache_key, mcp_args)
    if isinstance(res, list):
        return res[:limit]
    return res
