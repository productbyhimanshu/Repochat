# RepoChat — PRD

## Original Problem Statement
RepoChat is a **codebase comprehension layer** for the AI coding era. A user pastes a public
GitHub URL; before they ask a single question, RepoChat auto-analyzes the repo (file tree,
dependency graph, TODOs, churn, schema usage, architectural drift) and produces a 4-section
auto-brief. Then they can chat about the repo. The MVP is built on top of an existing
phased plan in `/app/doc/architeture.md` and `/app/doc/todo.md`. Phases 1–4 were already
complete; this session implemented **Phase 5 — React Frontend**.

## Target Personas
1. **Vibe Coder** (primary): non-technical founder who built with AI agents and no longer
   understands the system they shipped.
2. **Multi-IDE Developer**: technical user whose repos have outgrown their mental continuity.
3. **PM / Eng Lead** (secondary).

## Core Requirements (static)
- Paste a GitHub URL → automatic 4-section brief (architecture, core modules, hidden signals,
  unused data) in < 60s.
- After the brief, conversational Q&A with source citations.
- Hard rules (never break): only Orchestrator calls the LLM; only `mcp/github_client.py`
  calls GitHub; cache every fetch; no DB; no auth; public repos only.
- UI order is locked: URL input → loading → AutoBrief (primary) → Chat (secondary).

## Architecture (in /app)
```
React (Vite) · port 3000        FastAPI · port 8001 (Emergent ingress: /api → 8001)
        ↓ POST /api/{index,chat}
Orchestrator  ← only node that calls LLM
        ↓ asyncio.gather
Index Agent             Signal Agent
        ↓                   ↓
        └── github_client (REST) ──┘
                    ↓
        Claude Sonnet 4.5 (Emergent Universal Key)
                    ↓
            Rate Queue (15 RPM)
```

Stack: FastAPI · Python 3.11 · React 18 · Vite 5 · `emergentintegrations`
(`anthropic/claude-sonnet-4-5-20250929`).

## What's been implemented

### Phase 1–4 (already complete in repo on first pull)
- ✅ FastAPI skeleton, session store, GitHub REST client (cached), rate queue, LLM client,
  Index Agent, Signal Agent (incl. wow violations heuristic), Orchestrator + question
  classifier, real /index and /chat with Gemini.

### Phase 5 — React Frontend (this session — 2026-01-23)
- ✅ Cloned user's repo into `/app` with `.git` preserved so changes can be pushed to
  `origin = github.com/productbyhimanshu/Repochat.git`.
- ✅ Adapted backend to Emergent supervisor: renamed `main.py → server.py`, moved all routes
  under `/api`, kept session-store shape locked.
- ✅ Swapped LLM provider per user choice: **Gemini via OpenRouter → Claude Sonnet 4.5 via
  Emergent Universal Key** (`/app/backend/llm/llm_client.py`).
- ✅ Frontend rebuilt with editorial dark aesthetic:
  - Fonts: Instrument Serif (display) · Manrope (body) · JetBrains Mono (code)
  - Palette: warm dark with `#ff7a47` accent and gold/sage/violet semantic colours
  - Grain texture overlay, shimmering "wow" violation banner, micro-animations on hover
  - Three states: `idle → loading → brief_ready`
  - Loading view shows the 4 parallel-agent steps progressing
  - AutoBrief renders ALWAYS above Chat (architecture invariant verified)
  - AutoBrief: architecture · core modules (clickable to GitHub) · hidden signals
    (violation gets a "wow banner") · unused data
  - Chat: suggested prompt chips, markdown answers (react-markdown + remark-gfm), source
    chips that link to files on GitHub, sticky composer
  - `data-testid` on every interactive + critical element
- ✅ Frontend env wired to `REACT_APP_BACKEND_URL` via Vite `define`.
- ✅ Fixed 422 error normalisation (`api.js`) so Pydantic validator messages show as
  human text instead of `[object Object]`.

### Testing (iteration 1)
- Backend: **11/11 pytest tests pass** (health, /api/index valid+invalid, /api/chat
  unknown session, empty question, 5 classifier kinds all returning answers + sources).
- Frontend: full end-to-end flow validated on the public preview URL; AutoBrief renders
  before Chat (verified via `compareDocumentPosition`); all 1-shot bugs from the testing
  agent's report were addressed.

## Prioritized Backlog (Phase 6 polish — not done in this session)

### P0
- *None.* Phase 5 ships with all acceptance tests green.

### P1
- Phase 6 demo prep on `expressjs/express` to confirm the "outlier bypasses dominant
  pattern" violation lands cleanly in the wow banner.
- Switch FastAPI startup events from deprecated `@app.on_event` to the lifespan
  context manager.
- Detect repo's default branch in `fileUrl()` instead of hard-coding `HEAD`.

### P2
- Add a small "what would I add a feature here?" question template to the chat prompts.
- Show a session-history sidebar so the user can return to old briefs.
- Streamed LLM responses for the chat panel.
- Per-request progress polling so the Loading view reflects real backend state.

## How to push back to origin
The user owns the repo. `.git` in `/app` already points to
`https://github.com/productbyhimanshu/Repochat.git`. They can use the
**Save to GitHub** action in the chat input to push.

## Next Tasks
1. **Phase 6** — error boundaries, 0-state polish (already mostly covered), 200-file
   warning, final demo run on `expressjs/express` + `fastapi/fastapi`.
2. Add a tiny landing-page metric counter ("X repos analyzed") to nudge shareability.
