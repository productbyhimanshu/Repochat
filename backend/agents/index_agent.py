"""
index_agent.py — Extracts file tree and dependency graph.
"""
import asyncio
import re
from backend.mcp.github_client import get_file_tree, get_file_contents
from backend.session import require_session
from backend.logger import get_logger

log = get_logger("repochat.agents.index")

_IMPORT_RE = re.compile(r'(?:import|from|require)\s*\(?[\'"]([^\'"]+)[\'"]\)?')

async def run(owner: str, repo: str, session_id: str):
    log.agent("index_agent", f"Starting index agent for {owner}/{repo}")
    store = require_session(session_id)
    
    # 1. Fetch file tree
    tree = await get_file_tree(session_id, owner, repo)
    
    # Filter for source files to keep payload small
    src_exts = (".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs", ".java")
    source_files = [
        f for f in tree 
        if f.endswith(src_exts) 
        and "node_modules" not in f 
        and "test" not in f.lower() 
        and "dist/" not in f
    ][:30]  # limit to 30 to avoid MCP rate limits
    
    log.agent("index_agent", f"Selected {len(source_files)} source files for deep parsing")
    
    # 2. Fetch contents in parallel
    async def _fetch(f):
        try:
            return f, await get_file_contents(session_id, owner, repo, f)
        except Exception as e:
            log.agent("index_agent", f"Failed to fetch {f}: {e}")
            return f, ""

    results = await asyncio.gather(*[_fetch(f) for f in source_files])
    contents_map = {f: txt for f, txt in results}

    # 3. Build dep graph
    dep_graph = {}
    import_count = {f: 0 for f in source_files}
    referenced_by_count = {f: 0 for f in source_files}

    for f, txt in contents_map.items():
        imports = _IMPORT_RE.findall(txt)
        actual_imports = []
        for imp in imports:
            # simple heuristic: check if imported string matches part of another known file
            imp_clean = imp.strip("./").strip("../").split("/")[-1]
            if not imp_clean: continue
            
            for other_f in source_files:
                if other_f != f and imp_clean in other_f:
                    actual_imports.append(other_f)
                    break
                    
        dep_graph[f] = list(set(actual_imports))
        import_count[f] = len(dep_graph[f])
        for a_imp in dep_graph[f]:
            if a_imp in referenced_by_count:
                referenced_by_count[a_imp] += 1

    # 4. Score centrality
    centrality = {f: import_count.get(f, 0) + referenced_by_count.get(f, 0) for f in source_files}
    
    # 5. Top 8 files
    top_8_files = sorted(centrality.keys(), key=lambda x: centrality[x], reverse=True)[:8]
    
    # 6. Write to session
    for f in top_8_files:
        store["indexed_files"][f] = contents_map[f]
        
    store["dependency_graph"] = dep_graph
    
    log.agent("index_agent", "Finished. Dependency graph and top 8 files cached.")
