"""
stats.py — Persistent counter for "repos analyzed".

Architecture rule: no database. We use a small JSON file (atomic write)
to persist the counter across restarts. Single-process backend, so a
plain file lock is sufficient.
"""

import json
import os
import threading
from pathlib import Path

_STATE_DIR = Path(__file__).resolve().parent / "state"
_STATE_FILE = _STATE_DIR / "counter.json"
_LOCK = threading.Lock()


def _ensure_file() -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    if not _STATE_FILE.exists():
        _STATE_FILE.write_text(json.dumps({"repos_analyzed": 0}), encoding="utf-8")


def get_count() -> int:
    _ensure_file()
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return int(data.get("repos_analyzed", 0))
    except Exception:
        return 0


def increment() -> int:
    with _LOCK:
        _ensure_file()
        try:
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {"repos_analyzed": 0}
        count = int(data.get("repos_analyzed", 0)) + 1
        data["repos_analyzed"] = count
        tmp = _STATE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, _STATE_FILE)
        return count
