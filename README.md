# RepoChat

> AI made development cheap. Clarity became expensive. RepoChat restores it.

RepoChat is a codebase comprehension layer. Paste any public GitHub URL and it reads the repository end-to-end before you ask a single question — surfacing the architecture, the files that actually drive the system, signals buried in commit history and source code, and schema fields defined but never read. Then you talk to it. Every answer cites the exact source file it read.

RepoChat does not generate code, modify repositories, or require IDE installation. It is a read-only comprehension layer. The only input it accepts is a URL.

---

## What it does

Indexing runs silently the moment you paste a URL. Twelve parallel queries run across file structure, code signals, and data patterns. From those, a 4-section auto-brief renders before you ask anything: an architecture narrative, the top 8 files by centrality score with their roles and badges, hidden signals from TODO clusters and high-churn files including an architectural violation card when a file bypasses the dominant pattern, and schema fields defined but never referenced in processing code.

After the brief, a chat panel opens. Five question modes — architecture, flow, drift, signal, and module — are classified by keyword matching with no LLM cost. Every response includes source citations as clickable links pointing to the exact file in the repo's default branch on GitHub.

---

## How it works

**Phase 1 — Auto-Index**

On URL submit, `index_agent` and `signal_agent` run in parallel via `asyncio.gather`. Index Agent fetches the full file tree, filters to source files by extension (`.js .jsx .ts .tsx .py .go .rs .java .rb .php`), fetches up to 40 of them in parallel, builds a dependency graph from import statements, and scores each file by centrality:

```
centrality[file] = import_count[file] + referenced_by_count[file]
```

The top 8 by centrality are stored in session as `indexed_files`. Signal Agent runs concurrently: it searches for `TODO OR FIXME`, analyzes commit message frequency for the last 30 commits to identify high-churn files, scans indexed files for field definitions that appear only once (unused fields), and compares import patterns across files to flag architectural outliers.

**Phase 2 — Auto-Brief**

Once both agents complete, the Orchestrator builds a prompt from session data — top 8 files truncated to 1200 characters each — and calls Claude Sonnet 4.5. The LLM returns a structured JSON object with four sections. The Orchestrator writes it to `session_store["brief"]` and the API returns it immediately in the `/api/index` response. No polling required.

**Phase 3 — Conversational Chat**

Each question hits `POST /api/chat`. The classifier reads keywords, selects one of five modes, pulls the relevant slice of session data as context (no re-fetch — everything is already cached), builds a prompt, and calls the LLM. The response includes the answer and a `sources` array of file paths that fed the context.

---

## Architecture

```
React 18 + Vite (production build) ─────────── port 3000
         │
         │  POST /api/index
         │  POST /api/chat
         │  GET  /api/health
         │  GET  /api/stats
         ▼
FastAPI + Uvicorn ──────────────────────────── port 8001
         │
         ▼
    orchestrator.py  ◄── only caller of LLM
         │
         │  asyncio.gather()
         ├──────────────────────────┐
         ▼                          ▼
  index_agent.py           signal_agent.py
  · file tree              · search_code(TODO/FIXME)
  · dep graph              · list_commits(30) → churn
  · centrality score       · unused field regex scan
  · top 8 files            · dominant pattern diff
         │                          │
         └─────────────┬────────────┘
                       ▼
           mcp/github_client.py
           httpx → GitHub REST API v3
           session-level response cache
           
                       │ agents write to session_store
                       ▼
         session_store (in-memory Python dict)
         backend/state/counter.json  (repos_analyzed)

    orchestrator.py ──► llm/llm_client.py
                        emergentintegrations SDK
                        anthropic/claude-sonnet-4-5-20250929
                             │
                        llm/rate_queue.py
                        15 RPM sliding window
                        5-retry exponential backoff on 429
```

| Module | Does | Hard constraint |
|---|---|---|
| `orchestrator.py` | dispatches agents, classifies questions, calls LLM, writes brief | only module that calls LLM |
| `agents/index_agent.py` | file tree, dep graph, centrality scoring, top-8 selection | never calls LLM |
| `agents/signal_agent.py` | TODOs, churn, unused fields, architectural violations | never calls LLM |
| `mcp/github_client.py` | all GitHub REST calls, caches every result to session immediately | never contains business logic |
| `llm/rate_queue.py` | 15 RPM guard, retry on 429, exponential backoff | mandatory on every LLM call |

---

## Setup — Backend

**Requirements:** Python 3.11+

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GITHUB_TOKEN=ghp_...
EMERGENT_LLM_KEY=sk-emergent-...
```

Start the server:

```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

The server starts on port 8001. On startup it logs whether `GITHUB_TOKEN` and `EMERGENT_LLM_KEY` are set, and the current `repos_analyzed` count.

---

## Setup — Frontend

**Requirements:** Node.js 18+

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

**Development** (Vite dev server, HMR disabled):

```bash
npm run dev
```

**Production preview** (build then serve — matches deployed behavior):

```bash
npm start
```

Both serve on port 3000. The `npm start` script runs `vite build --mode production && vite preview`. Use this when running behind a reverse proxy — the production build has no HMR client and no WebSocket reconnect loops.

---

## Environment variables

| Variable | Required | Set in | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | Yes | `backend/.env` | GitHub personal access token with `public_repo` scope. Without it, GitHub's unauthenticated rate limit is 60 req/hour. The backend falls back to unauthenticated on 401 and raises an error on 403. |
| `EMERGENT_LLM_KEY` | Yes | `backend/.env` | Emergent Universal Key for Claude Sonnet 4.5. The server logs a warning on startup if missing. All LLM calls fail without it. |
| `REACT_APP_BACKEND_URL` | Yes | `frontend/.env` | Full URL of the backend, e.g. `http://localhost:8001`. Read by `frontend/src/lib/api.js` at build time via `vite.config.js`. |

---

## API reference

| Method | Path | Body | Success |
|---|---|---|---|
| GET | `/api/health` | — | 200 |
| GET | `/api/stats` | — | 200 |
| POST | `/api/index` | `{ "url": "https://github.com/owner/repo" }` | 200 |
| POST | `/api/chat` | `{ "session_id": "...", "question": "..." }` | 200 |

**GET /api/health**

```json
{
  "status": "ok",
  "version": "0.6.0",
  "github_token": "set",
  "llm_key": "set"
}
```

**GET /api/stats**

```json
{ "repos_analyzed": 42 }
```

**POST /api/index**

Request:
```json
{ "url": "https://github.com/expressjs/express" }
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "brief": {
    "architecture": "Express is a minimal Node.js web framework...",
    "core_modules": [
      { "file": "lib/application.js", "role": "Core app factory", "badge": "Core" }
    ],
    "hidden_signals": [
      { "type": "violation", "title": "...", "detail": "...", "source": "lib/router/index.js" }
    ],
    "unused_data": [
      { "field": "settings", "note": "defined but not read downstream", "tag": "Stale" }
    ]
  },
  "repo_meta": {
    "owner": "expressjs",
    "repo": "express",
    "url": "https://github.com/expressjs/express",
    "default_branch": "master",
    "total_files": 314
  },
  "repos_analyzed": 7
}
```

Errors: `422` invalid URL format · `502` GitHub rate limit hit · `500` unhandled failure

**POST /api/chat**

Request:
```json
{ "session_id": "550e8400-...", "question": "How does a request flow through the system?" }
```

Response:
```json
{
  "answer": "Requests enter through lib/application.js...",
  "sources": ["lib/application.js", "lib/router/index.js"]
}
```

Errors: `404` session not found · `422` empty question · `500` LLM failure

**Question classifier** (keyword-based, no LLM cost):

| Mode | Trigger keywords | Context pulled from session |
|---|---|---|
| `architecture` | *(default)* | `brief.architecture` + `brief.core_modules` |
| `flow` | flow, through, trace, path, request, response, moves, travels, pipeline | top 5 `indexed_files` + `dependency_graph` excerpt |
| `drift` | drift, changed, recent, unstable, broken, regressed, churn | `signals.violations` + `signals.churn` |
| `signal` | todo, fixme, hack, unused, signal, risk, hidden, warning, issue | `signals.todos` + `signals.unused_fields` |
| `module` | file, module, class, function, method, purpose, explain, what does, how does | best-match `indexed_files[file]` + its dep list |

---

## Running tests

The test suite runs against a live backend. Set `REACT_APP_BACKEND_URL` to point at your running instance before running.

```bash
# Start the backend first
cd backend && uvicorn server:app --host 0.0.0.0 --port 8001

# In a second terminal
REACT_APP_BACKEND_URL=http://localhost:8001 pytest backend/tests/backend_test.py -v
```

11 tests covering: `GET /api/health`, `GET /api/stats`, `POST /api/index` (valid repo + two invalid URL cases), `POST /api/chat` (200, 404 unknown session, 422 empty question, architecture and module classifier modes), `repo_meta.default_branch` detection, `total_files` count, and counter increment semantics.

Latest result: **11/11 passing**.

---

## Demo repos

These three repos index reliably and produce strong briefs:

- `https://github.com/expressjs/express` — violation signal fires on the router; churn concentrated in middleware files
- `https://github.com/fastapi/fastapi` — deep dependency graph; centrality scoring surfaces the dependency injection core
- `https://github.com/tj/commander.js` — compact codebase; clean architecture brief, good for verifying classifier modes

After the brief loads, try:
- *"How does a request flow through the system?"*
- *"What changed recently? Where is the drift?"*
- *"What are the TODOs and hidden risks?"*
