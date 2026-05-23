"""
main.py — FastAPI routes for Repochat.

Routes:
  POST /index  — receive GitHub URL, run orchestrator, return real brief + session_id
  POST /chat   — receive session_id + question, classify + answer via Gemini

Phase 4: mocks replaced with real orchestrator calls.
"""

import os
import re
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from logger import get_logger, log_endpoint
from session import create_session, require_session
import orchestrator

# ── env & logger ───────────────────────────────────────────────────────────────
load_dotenv()
log = get_logger("repochat.main")

_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
_GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")

if not _GITHUB_TOKEN:
    log.warning("GITHUB_TOKEN not set — GitHub calls will fail")
if not _GEMINI_KEY:
    log.warning("GEMINI_API_KEY not set — Gemini calls will fail")

# ── app ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Repochat API",
    description="AI-powered GitHub repository intelligence",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

log.info("Repochat API starting up")


# ── request models ─────────────────────────────────────────────────────────────

_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(/.*)?$"
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
    question:   str


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse_owner_repo(url: str) -> tuple:
    m = _GITHUB_URL_RE.match(url)
    if not m:
        raise ValueError(f"Cannot parse owner/repo from {url!r}")
    return m.group("owner"), m.group("repo")


# ── routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.post("/index")
@log_endpoint("POST /index")
async def index_repo(body: IndexRequest):
    """
    Receive a GitHub repo URL.
    Runs Index Agent + Signal Agent in parallel, then generates a 4-section brief via Gemini.
    """
    t0 = time.perf_counter()

    try:
        owner, repo = _parse_owner_repo(body.url)
    except ValueError as exc:
        log.api_error("POST /index", error=str(exc), url=body.url)
        raise HTTPException(status_code=422, detail=str(exc))

    log.info(f"Indexing {owner}/{repo}")
    session_id = create_session(owner=owner, repo=repo, url=body.url)

    try:
        brief = await orchestrator.run(owner, repo, session_id)
    except Exception as exc:
        log.api_error("POST /index", error=str(exc), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")

    duration_ms = (time.perf_counter() - t0) * 1000
    log.api_success("POST /index", duration_ms=duration_ms, session_id=session_id)

    return {"session_id": session_id, "brief": brief}


@app.post("/chat")
@log_endpoint("POST /chat")
async def chat(body: ChatRequest):
    """
    Classify the question, pull relevant session context, call Gemini, return answer + sources.
    """
    t0 = time.perf_counter()

    try:
        require_session(body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        result = await orchestrator.answer_question(body.session_id, body.question)
    except Exception as exc:
        log.api_error("POST /chat", error=str(exc), session_id=body.session_id)
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")

    duration_ms = (time.perf_counter() - t0) * 1000
    log.api_success("POST /chat", duration_ms=duration_ms, session_id=body.session_id)

    return result


# ── startup / shutdown ──────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    log.info("=" * 60)
    log.info("Repochat API ready (Phase 4 — real orchestrator)")
    log.info(f"  GITHUB_TOKEN : {'SET' if _GITHUB_TOKEN else 'MISSING ⚠'}")
    log.info(f"  GEMINI_KEY   : {'SET' if _GEMINI_KEY   else 'MISSING ⚠'}")
    log.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown():
    log.info("Repochat API shutting down")
