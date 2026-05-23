"""
index_agent.py — Extracts file tree, dependency graph, and centrality scores.
Stateless: reads from GitHub, writes to session_store. Never calls Gemini.
"""

import asyncio
import re

from mcp.github_client import get_file_tree, get_file_contents
from session import require_session
from logger import get_logger

log = get_logger("repochat.agents.index")

_IMPORT_RE = re.compile(r'(?:import|from|require)\s*\(?[\'"]([^\'"]+)[\'"]\)?')

_SRC_EXTS = (".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs", ".java", ".rb", ".php")
_SKIP_DIRS = ("node_modules", "dist/", ".next/", "build/", "vendor/", "__pycache__")
_SKIP_PATTERNS = ("test", "spec", ".min.", ".bundle.")


def _is_source_file(path: str) -> bool:
    if not path.endswith(_SRC_EXTS):
        return False
    lower = path.lower()
    if any(d in lower for d in _SKIP_DIRS):
        return False
    if any(p in lower for p in _SKIP_PATTERNS):
        return False
    return True


async def run(owner: str, repo: str, session_id: str) -> None:
    log.agent("index_agent", f"Starting for {owner}/{repo}")
    store = require_session(session_id)

    # 1. File tree
    tree = await get_file_tree(session_id, owner, repo)
    source_files = [f for f in tree if _is_source_file(f)][:40]
    log.agent("index_agent", f"Found {len(source_files)} source files")

    # 2. Fetch contents in parallel
    async def _fetch(path: str) -> tuple:
        try:
            return path, await get_file_contents(session_id, owner, repo, path)
        except Exception as exc:
            log.agent("index_agent", f"Failed to fetch {path}: {exc}")
            return path, ""

    results = await asyncio.gather(*[_fetch(f) for f in source_files])
    contents_map = {f: txt for f, txt in results if txt}

    # 3. Build dependency graph
    dep_graph: dict = {}
    import_count: dict = {f: 0 for f in source_files}
    referenced_by_count: dict = {f: 0 for f in source_files}

    for fname, txt in contents_map.items():
        raw_imports = _IMPORT_RE.findall(txt)
        resolved = []
        for imp in raw_imports:
            base = imp.strip("./").split("/")[-1].split(".")[0]
            if not base:
                continue
            for other in source_files:
                if other != fname and base.lower() in other.lower():
                    resolved.append(other)
                    break
        dep_graph[fname] = list(set(resolved))
        import_count[fname] = len(dep_graph[fname])
        for r in dep_graph[fname]:
            if r in referenced_by_count:
                referenced_by_count[r] += 1

    # 4. Centrality = import_count + referenced_by_count
    centrality = {
        f: import_count.get(f, 0) + referenced_by_count.get(f, 0)
        for f in source_files
    }

    # 5. Top 8 by centrality
    top_8 = sorted(centrality, key=lambda x: centrality[x], reverse=True)[:8]

    # 6. Write to session
    for f in top_8:
        if f in contents_map:
            store["indexed_files"][f] = contents_map[f]

    store["dependency_graph"] = dep_graph

    log.agent("index_agent", f"Done. Top files: {top_8}")
