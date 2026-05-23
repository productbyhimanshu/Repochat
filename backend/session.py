"""
session.py — In-memory session store for Repochat.

Shape is LOCKED. Never change top-level keys.
Add nested fields freely, never remove or rename existing ones.
"""

import time
import uuid
from typing import Any

# ── Session store (single Python dict, no database) ───────────────────────────
# Key: session_id (str UUID)
# Value: session shape below
session_store: dict[str, dict] = {}


def create_session(owner: str, repo: str, url: str) -> str:
    """
    Create a new session, initialise it with the exact shape from ARCHITECTURE.md,
    and return the session_id.
    """
    session_id = str(uuid.uuid4())

    session_store[session_id] = {
        # ── repo identity ──────────────────────────────────────────────────
        "repo_meta": {
            "owner":     owner,
            "repo":      repo,
            "url":       url,
            "timestamp": time.time(),
            "default_branch": "main",
            "total_files": 0,
        },

        # ── raw file content cache — never fetch same file twice ───────────
        # { filename: content_string }
        "indexed_files": {},

        # ── import graph — built by Index Agent ───────────────────────────
        # { filename: [imported_file_1, imported_file_2, ...] }
        "dependency_graph": {},

        # ── signals — built by Signal Agent ──────────────────────────────
        "signals": {
            "todos": [],
            # [ { "file": str, "count": int, "lines": [str] } ]

            "churn": [],
            # [ { "file": str, "commit_count": int } ]

            "unused_fields": [],
            # [ { "field": str, "defined_in": str, "note": str } ]

            "violations": [],
            # [ { "file": str, "pattern": str, "violation": str } ]
        },

        # ── auto-brief — assembled by Orchestrator via Gemini ─────────────
        "brief": {
            "architecture": "",
            # str — narrative summary of repo structure

            "core_modules": [],
            # [ { "file": str, "role": str, "badge": str } ]

            "hidden_signals": [],
            # [ { "type": str, "title": str, "detail": str, "source": str } ]

            "unused_data": [],
            # [ { "field": str, "note": str, "tag": str } ]
        },

        # ── session-level timestamp (for TTL / cleanup if needed later) ───
        "timestamp": time.time(),
    }

    return session_id


def get_session(session_id: str) -> dict | None:
    """Return the session dict, or None if not found."""
    return session_store.get(session_id)


def require_session(session_id: str) -> dict:
    """Return the session dict or raise ValueError."""
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Session not found: {session_id!r}")
    return session


def list_sessions() -> list[str]:
    """Return all active session IDs."""
    return list(session_store.keys())
