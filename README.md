# RepoChat

> Paste a public GitHub URL. Before you ask a single question, RepoChat reads the repo
> end-to-end and tells you how it's structured, what's drifting, and which files are
> quietly accumulating risk.

**Core insight:** AI made development cheap. **Clarity became expensive.** RepoChat restores it.

---

## What it does

1. **Paste a GitHub URL** — any public repo
2. **Auto-Brief appears** — 4 sections generated before you ask anything:
   - **Architecture** — narrative summary of how the system is built
   - **Core Modules** — top 8 files by centrality score, with role + badge
   - **Hidden Signals** — TODO clusters, high-churn files, and a "wow" architectural
     violation banner when a file bypasses the dominant pattern
   - **Unused Data** — schema fields defined but never referenced
3. **Conversational chat** with source citations:
   - *"How is this architecture structured?"* → architecture mode
   - *"How does a request flow through the system?"* → flow mode
   - *"What changed recently?"* → drift mode
   - *"What are the TODOs and hidden risks?"* → signal mode
   - *"What does middleware.js do?"* → module mode

RepoChat **does not** generate code, modify the repo, or require an IDE plugin.

---

## Architecture

```
React (Vite, production build) · port 3000
        ↓ HTTP /api/{index, chat, stats, health}
FastAPI · port 8001 · Python 3.11
        ↓
Orchestrator           ← only node that calls the LLM
        ↓ asyncio.gather
Index Agent       Signal Agent
        ↓               ↓
        └── GitHub REST client (cached) ──┘
                       ↓
        Claude Sonnet 4.5 (via Emergent Universal Key)
                       ↓
                Rate Queue (15 RPM)
```

| Agent           | Does                                                     | Does not             |
|-----------------|----------------------------------------------------------|----------------------|
| Orchestrator    | dispatches agents, classifies questions, calls the LLM   | call GitHub directly |
| Index Agent     | file tree, dep graph, centrality scoring, top 8 files    | call the LLM         |
| Signal Agent    | TODOs, commit churn, unused fields, arch violations      | call the LLM         |
| GitHub client   | all REST API calls, caches results immediately           | contain business logic |
| Rate Queue      | 15 RPM guard, retry on 429, exponential backoff          | know about agents    |

**Question classifier** (keyword-based, no LLM cost):

- `architecture` → `brief.architecture` + `core_modules`
- `flow`         → `indexed_files` + dependency graph
- `drift`        → `signals.violations` + `signals.churn`
- `signal`       → `signals.todos` + `signals.unused_fields`
- `module`       → `indexed_files[file]` + dep graph

---

## Status

| Phase   | Description                                                         | Status |
|---------|---------------------------------------------------------------------|--------|
| Phase 1 | FastAPI skeleton, session store, React stubs                        | ✅ Complete |
| Phase 2 | GitHub REST client, 15-RPM rate queue, LLM client                   | ✅ Complete |
| Phase 3 | Index Agent + Signal Agent                                          | ✅ Complete |
| Phase 4 | Orchestrator + question classifier + real brief generation          | ✅ Complete |
| Phase 5 | React frontend (URL input → loading → auto-brief → chat)            | ✅ Complete |
| Phase 6 | Polish: error boundary, large-repo warning, `repos understood` counter, lifespan ctx, default-branch detection | ✅ Complete |

---

## Stack

- **Backend:** FastAPI · Python 3.11 · `httpx` · `emergentintegrations`
- **Frontend:** React 18 · Vite 5 (production build, no HMR) · `react-markdown` · `lucide-react`
- **LLM:** `anthropic/claude-sonnet-4-5-20250929` via the Emergent Universal Key
- **GitHub data:** GitHub REST API v3 (authenticated, 5000 req/hour)
- **Session store:** In-memory Python dict (no database)
- **Counter persistence:** Atomic JSON file at `backend/state/counter.json`

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A GitHub personal access token (`public_repo` scope) → put in `backend/.env` as
  `GITHUB_TOKEN`
- An LLM key → either the Emergent Universal Key (`EMERGENT_LLM_KEY`) or your own
  Anthropic key

### Backend

```bash
# From project root
pip install -r requirements.txt
# Or: pip install -r backend/requirements.txt

# Configure environment
cp backend/.env.example backend/.env  # if you keep an example file
# Add:
#   GITHUB_TOKEN=ghp_...
#   EMERGENT_LLM_KEY=sk-emergent-...

cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd frontend
yarn install

# Configure:
# frontend/.env should contain
#   REACT_APP_BACKEND_URL=http://localhost:8001

# Dev (HMR enabled — local only)
yarn dev

# Production preview (matches how it's served in deployment — no HMR)
yarn start
```

Both modes serve on **port 3000**.

> **Why production build by default?** In dev mode, Vite's HMR client tries to maintain a
> WebSocket connection. When the app is served behind a reverse proxy (e.g. Kubernetes
> ingress), that WebSocket can flap and Vite's reconnect-on-disconnect logic produces
> visible page-reload loops. The production build has no HMR client → no reload loop.

### Test the API

```bash
# Index a repo
curl -X POST http://localhost:8001/api/index \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/expressjs/express"}'

# Chat (use session_id from above response)
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "question": "How is this architecture structured?"}'

# Counter
curl http://localhost:8001/api/stats
# → {"repos_analyzed": 42}
```

---

## API

| Method | Path           | Body                                  | Returns                                                              |
|--------|----------------|---------------------------------------|----------------------------------------------------------------------|
| GET    | `/api/health`  | —                                     | `{ status, version, github_token, llm_key }`                         |
| GET    | `/api/stats`   | —                                     | `{ repos_analyzed: int }`                                            |
| POST   | `/api/index`   | `{ url }`                             | `{ session_id, brief, repo_meta, repos_analyzed }`                   |
| POST   | `/api/chat`    | `{ session_id, question }`            | `{ answer, sources[] }`                                              |

`repo_meta` includes: `owner`, `repo`, `url`, `default_branch`, `total_files`.
`brief` always has 4 sections: `architecture`, `core_modules`, `hidden_signals`, `unused_data`.

---

## Session-store shape (locked)

```python
session_store[session_id] = {
    "repo_meta": {
        "owner": str, "repo": str, "url": str,
        "timestamp": float,
        "default_branch": str,
        "total_files": int,
    },
    "indexed_files":    { "filename": "content_string" },
    "dependency_graph": { "filename": ["imported_file_1", ...] },
    "signals": {
        "todos":         [{ "file": str, "count": int, "lines": [str] }],
        "churn":         [{ "file": str, "commit_count": int }],
        "unused_fields": [{ "field": str, "defined_in": str, "note": str }],
        "violations":    [{ "file": str, "pattern": str, "violation": str }],
    },
    "brief": {
        "architecture":   str,
        "core_modules":   [{ "file": str, "role": str, "badge": str }],
        "hidden_signals": [{ "type": str, "title": str, "detail": str, "source": str }],
        "unused_data":    [{ "field": str, "note": str, "tag": str }],
    },
    "timestamp": float,
}
```

Top-level keys are **never** renamed or removed; nested fields may grow.

---

## Hard rules (never break)

- Only `orchestrator.py` calls the LLM
- Only `mcp/github_client.py` calls GitHub
- Cache every GitHub fetch to the session store — never fetch the same file twice
- No database — session store is a Python dict; counter is a JSON file
- No vector DB, no embeddings, no graph visualisation library
- No auth — public repos only
- Rate queue is mandatory on every LLM call
- Agents are stateless: inputs in, outputs out, session write only
- UI order is locked: URL input → loading → **AutoBrief** (primary) → **Chat** (secondary)

---

## Testing

- `pytest backend/tests/backend_test.py` — 11 tests covering health, stats, /index
  (valid + 422), /chat (200, 404, 422, all 5 classifier kinds), `repo_meta.default_branch`,
  `total_files`, and counter increment semantics.
- Frontend has full `data-testid` coverage for browser-automation tests.

Latest run: **backend 11/11**, **frontend 100%** on all flows (landing → loading →
brief → chat → reset, large-repo warning, error boundary).

---

## Demo

Try these in the live demo:
- `https://github.com/expressjs/express`
- `https://github.com/fastapi/fastapi`
- `https://github.com/tj/commander.js`

After the brief loads, ask:
- *"How does a request flow through the system?"*
- *"What changed recently? Where is the drift?"*
- *"What are the TODOs and hidden risks?"*

---

*Built by [Himanshu](https://github.com/productbyhimanshu).*
