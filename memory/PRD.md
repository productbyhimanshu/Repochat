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

### Phase 5 — React Frontend (2026-01-23)
- ✅ Cloned user's repo into `/app` with `.git` preserved so changes can be pushed to
  `origin = github.com/productbyhimanshu/Repochat.git`.
- ✅ Adapted backend to Emergent supervisor: renamed `main.py → server.py`, moved all routes
  under `/api`, kept session-store shape locked.
- ✅ Swapped LLM provider per user choice: **Gemini via OpenRouter → Claude Sonnet 4.5 via
  Emergent Universal Key** (`/app/backend/llm/llm_client.py`).
- ✅ Frontend rebuilt with editorial dark aesthetic (Instrument Serif · Manrope · JetBrains
  Mono · warm orange `#ff7a47`, grain overlay, micro-animations).
- ✅ Three states: `idle → loading → brief_ready`; AutoBrief renders ALWAYS above Chat.
- ✅ AutoBrief: architecture · core modules · hidden signals (violation wow banner) ·
  unused data.
- ✅ Chat: suggested prompts, markdown answers, source chips that link to files on GitHub.
- ✅ `data-testid` on every interactive element.
- ✅ Fixed 422 error normalisation in `api.js` (no more `[object Object]`).

### Phase 6 — Polish + Counter (2026-01-23)
- ✅ **ErrorBoundary** wraps the app in `main.jsx` — no more blank screen on render errors.
- ✅ **RepoSizeBanner** appears in the brief when `repo_meta.total_files > 200`.
- ✅ **`/api/stats`** endpoint + persistent counter at `/app/backend/state/counter.json`
  with thread-safe atomic writes.
- ✅ **StatsCounter chip** on the landing page ("X repos understood") — shareability hook.
- ✅ Counter increments only on a successful `/api/index`; 422-invalid URLs do not bump it.
- ✅ Migrated FastAPI `@app.on_event` startup/shutdown → **lifespan context manager**.
- ✅ `default_branch` detection: `mcp/github_client.get_file_tree` writes it to `repo_meta`,
  frontend `fileUrl()` uses it (so commander.js links resolve to `/blob/master/...` instead
  of `/blob/HEAD/...`).
- ✅ `repo_meta.total_files` populated by index_agent so the banner has data to react to.

### Testing
- Iteration 1 (Phase 5): backend 11/11 pass, frontend ~95% (one minor 422-display bug fixed).
- Iteration 2 (Phase 6): backend 11/11 pass, frontend 100% on tested flows, zero new bugs.
  Verified live: `stats-counter` shows numeric count, `repo-size-banner` shows '223 files',
  module hrefs use `/blob/master/`, ErrorBoundary invisible on happy path.

## Prioritized Backlog

### P0
- *None.* MVP + Phase 6 polish + counter all shipped & tested.

### P1
- Final demo runs on `expressjs/express` + `fastapi/fastapi` to confirm the "outlier
  bypasses dominant pattern" wow violation lands cleanly.
- Move AutoBrief.jsx's `useMemo` calls above the early `return null` for stricter
  rules-of-hooks compliance (currently tolerated).
- If we ever switch to multi-worker uvicorn, replace `threading.Lock` in `stats.py` with
  `fcntl` file-locking or move the counter into the in-memory session store.

### P2
- Streamed LLM responses for the chat panel.
- Per-request progress polling so the Loading view reflects real backend state.
- Session-history sidebar (revisit old briefs).
- "Where would I add this feature?" suggested chat prompt.

## How to push back to origin
The user owns the repo. `.git` in `/app` already points to
`https://github.com/productbyhimanshu/Repochat.git`. They can use the
**Save to GitHub** action in the chat input to push.

## Next Tasks
1. **Phase 6** — error boundaries, 0-state polish (already mostly covered), 200-file
   warning, final demo run on `expressjs/express` + `fastapi/fastapi`.
2. Add a tiny landing-page metric counter ("X repos analyzed") to nudge shareability.
