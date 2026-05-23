"""
server.py — FastAPI app for RepoChat (Phase 6).

All routes mounted under /api so they route through the Emergent ingress.

Routes:
  POST /api/index   — receive GitHub URL, run orchestrator, return brief + session_id
  POST /api/chat    — receive session_id + question, classify + answer via Claude
  GET  /api/health  — liveness
  GET  /api/stats   — total repos analyzed (for landing-page counter)
"""

import os
import re
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

# ── env (MUST load before importing anything that reads env) ──────────────────
load_dotenv()

from logger import get_logger, log_endpoint  # noqa: E402
from session import create_session, require_session  # noqa: E402
import orchestrator  # noqa: E402
import stats  # noqa: E402

log = get_logger("repochat.server")

_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
_EMERGENT_KEY = os.getenv("EMERGENT_LLM_KEY", "")

if not _GITHUB_TOKEN:
    log.warning("GITHUB_TOKEN not set — GitHub calls will fail")
if not _EMERGENT_KEY:
    log.warning("EMERGENT_LLM_KEY not set — LLM calls will fail")


# ── lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info(f"RepoChat API ready (v{app.version} — Phase 6)")
    log.info(f"  GITHUB_TOKEN     : {'SET' if _GITHUB_TOKEN else 'MISSING'}")
    log.info(f"  EMERGENT_LLM_KEY : {'SET' if _EMERGENT_KEY else 'MISSING'}")
    log.info(f"  repos_analyzed   : {stats.get_count()}")
    log.info("=" * 60)
    yield
    log.info("RepoChat API shutting down")


# ── app ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RepoChat API",
    description="AI-powered GitHub repository comprehension layer",
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")

log.info("RepoChat API starting up")


# ── request models ─────────────────────────────────────────────────────────────

_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s?#]+?)(?:\.git)?(?:/.*)?/?$"
)


class IndexRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        if not _GITHUB_URL_RE.match(v.strip()):
            raise ValueError(
                "URL must be a valid GitHub repository URL (https://github.com/owner/repo)"
            )
        return v.strip()


class ChatRequest(BaseModel):
    session_id: str
    question: str


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse_owner_repo(url: str) -> tuple:
    m = _GITHUB_URL_RE.match(url)
    if not m:
        raise ValueError(f"Cannot parse owner/repo from {url!r}")
    return m.group("owner"), m.group("repo")


# ── routes ─────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "version": app.version,
        "github_token": "set" if _GITHUB_TOKEN else "missing",
        "llm_key": "set" if _EMERGENT_KEY else "missing",
    }


@router.get("/stats")
async def get_stats():
    return {"repos_analyzed": stats.get_count()}


@router.post("/index")
@log_endpoint("POST /api/index")
async def index_repo(body: IndexRequest):
    """Run Index Agent + Signal Agent in parallel, then generate a 4-section brief via Claude."""
    t0 = time.perf_counter()

    try:
        owner, repo = _parse_owner_repo(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    log.info(f"Indexing {owner}/{repo}")
    session_id = create_session(owner=owner, repo=repo, url=body.url)

    try:
        brief = await orchestrator.run(owner, repo, session_id)
    except RuntimeError as exc:
        log.api_error("POST /api/index", error=str(exc), session_id=session_id)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        log.api_error("POST /api/index", error=str(exc), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")

    # Counter increment is non-blocking & best-effort
    try:
        new_count = stats.increment()
    except Exception as exc:
        log.warning(f"counter increment failed: {exc}")
        new_count = stats.get_count()

    store = require_session(session_id)
    repo_meta = store.get("repo_meta", {})

    duration_ms = (time.perf_counter() - t0) * 1000
    log.api_success("POST /api/index", duration_ms=duration_ms, session_id=session_id)

    return {
        "session_id": session_id,
        "brief": brief,
        "repo_meta": {
            "owner":          repo_meta.get("owner", owner),
            "repo":           repo_meta.get("repo", repo),
            "url":            repo_meta.get("url", body.url),
            "default_branch": repo_meta.get("default_branch", "main"),
            "total_files":    repo_meta.get("total_files", 0),
        },
        "repos_analyzed": new_count,
    }


@router.post("/chat")
@log_endpoint("POST /api/chat")
async def chat(body: ChatRequest):
    """Classify question, pull session context, call Claude, return answer + sources."""
    t0 = time.perf_counter()

    try:
        require_session(body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not body.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")

    try:
        result = await orchestrator.answer_question(body.session_id, body.question.strip())
    except Exception as exc:
        log.api_error("POST /api/chat", error=str(exc), session_id=body.session_id)
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")

    duration_ms = (time.perf_counter() - t0) * 1000
    log.api_success("POST /api/chat", duration_ms=duration_ms, session_id=body.session_id)

    return result


app.include_router(router)
