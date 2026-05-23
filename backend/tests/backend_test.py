"""
backend_test.py — Pytest suite for RepoChat backend.

Covers:
  - GET  /api/health
  - POST /api/index (valid + invalid URL)
  - POST /api/chat  (valid session, unknown session, classifier coverage)
"""

import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-codebase-2.preview.emergentagent.com").rstrip("/")

# Small, stable, public repo per agent_to_agent_context_note
TEST_REPO_URL = "https://github.com/tj/commander.js"

# ----------------------------------------------------------------------------
# Module-level shared state for session reuse
# ----------------------------------------------------------------------------
_indexed = {"session_id": None, "brief": None, "repo_meta": None, "repos_analyzed": None}
_stats_before = {"value": None}


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ----------------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------------
class TestHealth:
    def test_health_ok(self, api):
        r = api.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["github_token"] == "set"
        assert data["llm_key"] == "set"
        assert "version" in data


# ----------------------------------------------------------------------------
# /api/index
# ----------------------------------------------------------------------------
class TestIndex:
    def test_index_invalid_url_returns_422(self, api):
        r = api.post(f"{BASE_URL}/api/index", json={"url": "not a url"}, timeout=15)
        assert r.status_code == 422
        data = r.json()
        assert "detail" in data

    def test_index_non_github_url_returns_422(self, api):
        r = api.post(f"{BASE_URL}/api/index", json={"url": "https://gitlab.com/foo/bar"}, timeout=15)
        assert r.status_code == 422

    def test_stats_before_index(self, api):
        """Capture counter value BEFORE the successful index. Also asserts /api/stats shape."""
        r = api.get(f"{BASE_URL}/api/stats", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "repos_analyzed" in data
        assert isinstance(data["repos_analyzed"], int)
        assert data["repos_analyzed"] >= 0
        _stats_before["value"] = data["repos_analyzed"]

    def test_stats_invalid_url_does_not_increment(self, api):
        """A 422-invalid URL must NOT increment the counter."""
        before = api.get(f"{BASE_URL}/api/stats", timeout=15).json()["repos_analyzed"]
        bad = api.post(f"{BASE_URL}/api/index", json={"url": "definitely not a url"}, timeout=15)
        assert bad.status_code == 422
        after = api.get(f"{BASE_URL}/api/stats", timeout=15).json()["repos_analyzed"]
        assert after == before, f"counter changed on invalid URL: {before} -> {after}"

    def test_index_valid_repo_returns_brief(self, api):
        """End-to-end indexing of a small public repo. May take 30-60s."""
        r = api.post(
            f"{BASE_URL}/api/index",
            json={"url": TEST_REPO_URL},
            timeout=180,
        )
        assert r.status_code == 200, f"index failed: {r.status_code} {r.text[:500]}"
        data = r.json()

        # Schema checks
        assert "session_id" in data and isinstance(data["session_id"], str) and len(data["session_id"]) > 0
        assert "brief" in data and isinstance(data["brief"], dict)
        assert "repo_meta" in data

        brief = data["brief"]
        for key in ("architecture", "core_modules", "hidden_signals", "unused_data"):
            assert key in brief, f"missing brief.{key}"

        assert isinstance(brief["architecture"], str) and len(brief["architecture"]) > 20
        assert isinstance(brief["core_modules"], list)
        assert isinstance(brief["hidden_signals"], list)
        assert isinstance(brief["unused_data"], list)

        # repo_meta
        meta = data["repo_meta"]
        assert meta["owner"] == "tj"
        assert meta["repo"] == "commander.js"
        assert meta["url"] == TEST_REPO_URL
        # Phase 6: repo_meta now includes default_branch & total_files
        assert "default_branch" in meta, "repo_meta.default_branch missing"
        assert meta["default_branch"] == "master", (
            f"commander.js default_branch should be 'master', got {meta['default_branch']!r}"
        )
        assert "total_files" in meta and isinstance(meta["total_files"], int)
        assert meta["total_files"] > 200, f"total_files should be >200, got {meta['total_files']}"

        # Phase 6: response now includes repos_analyzed
        assert "repos_analyzed" in data and isinstance(data["repos_analyzed"], int)
        _indexed["repos_analyzed"] = data["repos_analyzed"]

        # share to subsequent tests
        _indexed["session_id"] = data["session_id"]
        _indexed["brief"] = brief
        _indexed["repo_meta"] = meta

    def test_stats_incremented_by_one(self, api):
        """Counter increments by exactly 1 after a successful index."""
        if _stats_before["value"] is None or _indexed["repos_analyzed"] is None:
            pytest.skip("prior tests didn't run")
        # The response's repos_analyzed should equal before+1
        assert _indexed["repos_analyzed"] == _stats_before["value"] + 1, (
            f"expected {_stats_before['value']+1}, got {_indexed['repos_analyzed']}"
        )
        # And /api/stats should reflect the same
        r = api.get(f"{BASE_URL}/api/stats", timeout=15)
        assert r.status_code == 200
        assert r.json()["repos_analyzed"] >= _indexed["repos_analyzed"]


# ----------------------------------------------------------------------------
# /api/chat
# ----------------------------------------------------------------------------
class TestChat:
    def test_chat_unknown_session_returns_404(self, api):
        r = api.post(
            f"{BASE_URL}/api/chat",
            json={"session_id": "does-not-exist-xyz", "question": "what is this?"},
            timeout=30,
        )
        assert r.status_code == 404

    def test_chat_empty_question_returns_422(self, api):
        if not _indexed["session_id"]:
            pytest.skip("indexing test must run first")
        r = api.post(
            f"{BASE_URL}/api/chat",
            json={"session_id": _indexed["session_id"], "question": "   "},
            timeout=30,
        )
        assert r.status_code == 422

    @pytest.mark.parametrize(
        "label,question",
        [
            ("architecture", "How is this architecture structured?"),
            ("module", "What does index.js do?"),
        ],
    )
    def test_chat_classifier_kinds(self, api, label, question):
        if not _indexed["session_id"]:
            pytest.skip("indexing test must run first")

        r = api.post(
            f"{BASE_URL}/api/chat",
            json={"session_id": _indexed["session_id"], "question": question},
            timeout=120,
        )
        assert r.status_code == 200, f"chat[{label}] failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert "answer" in data and isinstance(data["answer"], str) and len(data["answer"]) > 5
        assert "sources" in data and isinstance(data["sources"], list)
        # pace requests slightly to respect 15 RPM guard
        time.sleep(2)
