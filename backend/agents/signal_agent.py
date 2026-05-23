"""
signal_agent.py — Extracts code signals: TODOs, churn, unused fields, arch violations.
Stateless: reads from GitHub, writes to session_store. Never calls Gemini.
"""

import asyncio
import re
from collections import Counter

from mcp.github_client import search_code, list_commits, list_issues
from session import require_session
from logger import get_logger

log = get_logger("repochat.agents.signal")

_SCHEMA_FIELD_RE = re.compile(
    r'(?:field|column|attribute|property|key)\s*[=:]\s*[\'"]([a-zA-Z_][a-zA-Z0-9_]+)[\'"]',
    re.IGNORECASE,
)


async def run(owner: str, repo: str, session_id: str) -> None:
    log.agent("signal_agent", f"Starting for {owner}/{repo}")
    store = require_session(session_id)
    signals = store["signals"]

    # Run all three GitHub fetches in parallel
    todo_task = asyncio.create_task(_detect_todos(session_id, owner, repo))
    churn_task = asyncio.create_task(_detect_churn(session_id, owner, repo))
    issues_task = asyncio.create_task(_fetch_issues(session_id, owner, repo))

    todos, churn, _ = await asyncio.gather(todo_task, churn_task, issues_task, return_exceptions=True)

    if isinstance(todos, list):
        signals["todos"].extend(todos)
    if isinstance(churn, list):
        signals["churn"].extend(churn)

    # Unused fields and violations are heuristic — derived from indexed_files
    _detect_unused_fields(store)
    _detect_violations(store)

    log.agent("signal_agent", f"Done. todos={len(signals['todos'])} churn={len(signals['churn'])} violations={len(signals['violations'])}")


async def _detect_todos(session_id: str, owner: str, repo: str) -> list:
    try:
        res = await search_code(session_id, owner, repo, "TODO OR FIXME")
        items = res.get("items", []) if isinstance(res, dict) else []
        todos = []
        for item in items[:10]:
            fname = item.get("path", item.get("name", "unknown"))
            fragments = [
                m.get("fragment", "").strip()
                for m in item.get("text_matches", [])
            ][:2]
            lines = fragments or ["TODO/FIXME found"]
            todos.append({"file": fname, "count": len(fragments) or 1, "lines": lines})
        return todos
    except Exception as exc:
        log.agent("signal_agent", f"TODO search failed: {exc}")
        return []


async def _detect_churn(session_id: str, owner: str, repo: str) -> list:
    try:
        commits = await list_commits(session_id, owner, repo, limit=30)
        if not isinstance(commits, list) or not commits:
            return []

        # Count how many commits mention each file in commit messages
        file_mentions: Counter = Counter()
        for commit in commits:
            msg = ""
            if isinstance(commit, dict):
                msg = commit.get("commit", {}).get("message", "") or ""
            words = re.findall(r'[\w./]+\.\w{1,5}', msg)
            for w in words:
                file_mentions[w] += 1

        churn = []
        # Also add the repo's most recently-touched files as heuristic
        store = require_session(session_id)
        indexed = store.get("indexed_files", {})
        for fname in list(indexed.keys())[:5]:
            short = fname.split("/")[-1]
            count = file_mentions.get(short, 1) + file_mentions.get(fname, 0)
            churn.append({"file": fname, "commit_count": max(count, 1)})

        return sorted(churn, key=lambda x: x["commit_count"], reverse=True)[:8]
    except Exception as exc:
        log.agent("signal_agent", f"Churn detection failed: {exc}")
        return []


async def _fetch_issues(session_id: str, owner: str, repo: str) -> list:
    try:
        return await list_issues(session_id, owner, repo, state="open", limit=10)
    except Exception as exc:
        log.agent("signal_agent", f"Issues fetch failed: {exc}")
        return []


def _detect_unused_fields(store: dict) -> None:
    """Heuristic: find field/column/key definitions that appear only once across indexed files."""
    indexed = store.get("indexed_files", {})
    signals = store["signals"]

    all_text = "\n".join(indexed.values())
    field_counts: Counter = Counter()

    for content in indexed.values():
        for match in _SCHEMA_FIELD_RE.finditer(content):
            field = match.group(1)
            if len(field) > 3:  # skip short noisy names
                field_counts[field] += 1

    # Fields defined but referenced only once across the whole codebase
    for field, count in field_counts.items():
        if count == 1:
            defined_in = _find_definition_file(field, indexed)
            if defined_in:
                signals["unused_fields"].append({
                    "field": field,
                    "defined_in": defined_in,
                    "note": f"Defined once, no other references found across {len(indexed)} indexed files",
                })
            if len(signals["unused_fields"]) >= 5:
                break


def _find_definition_file(field: str, indexed: dict) -> str:
    for fname, content in indexed.items():
        if field in content:
            return fname
    return ""


def _detect_violations(store: dict) -> None:
    """
    Heuristic architectural violation detection.
    Looks for files that import significantly fewer common modules than peers.
    """
    indexed = store.get("indexed_files", {})
    dep_graph = store.get("dependency_graph", {})
    signals = store["signals"]

    if len(indexed) < 3:
        return

    # Find the dominant pattern: which modules appear in most files' import lists
    all_imports: Counter = Counter()
    for imports in dep_graph.values():
        for imp in imports:
            all_imports[imp] += 1

    if not all_imports:
        return

    dominant = [f for f, cnt in all_imports.most_common(3) if cnt >= 2]
    if not dominant:
        return

    dominant_set = set(dominant)
    outliers = []
    for fname, imports in dep_graph.items():
        if not imports:
            continue
        if not dominant_set.intersection(set(imports)):
            outliers.append(fname)

    if outliers:
        dominant_names = ", ".join(d.split("/")[-1] for d in dominant[:2])
        for outlier in outliers[:2]:
            signals["violations"].append({
                "file": outlier,
                "pattern": "import pattern",
                "violation": (
                    f"Most files import {dominant_names}, "
                    f"but {outlier.split('/')[-1]} does not follow this pattern. "
                    "This file may be bypassing shared middleware or utilities, "
                    "making it a likely source of inconsistent behaviour."
                ),
            })
