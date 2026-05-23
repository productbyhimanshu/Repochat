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
_indexed = {"session_id": None, "brief": None, "repo_meta": None}


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

        # share to subsequent tests
        _indexed["session_id"] = data["session_id"]
        _indexed["brief"] = brief
        _indexed["repo_meta"] = meta


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
            ("flow", "How does a request flow through commander?"),
            ("drift", "What changed recently? Where is the drift?"),
            ("signal", "What TODOs and hidden risks exist?"),
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
