# ARCHITECTURE.md
> Read this file completely before writing any code.
> Update the Current State section at the end of every session.

---

## What This Is

**RepoChat** — paste any public GitHub URL, get a plain-English brief about the codebase before asking a single question.

**Who it is for:** people who built with AI agents and no longer understand what they shipped.

**Core insight:** Development became cheap. Clarity became expensive.

**The magic moment:** before the user asks anything, the product shows them things about their own code they did not know existed.

---

## Stack

```
React (Vite) · localhost:3000
      ↓ HTTP / REST
FastAPI · localhost:8000 · Python 3.11
      ↓
Orchestrator Agent          ← top node, only node that calls Gemini
      ↓ parallel dispatch
Index Agent    Session Store    Signal Agent
      ↓                               ↓
      └──────── GitHub MCP ───────────┘
                     ↓
            Gemini 2.5 Flash Lite (free tier)
                     ↓
            Rate Limit Queue (15 RPM guard)
```

---

## File Structure

```
repochat/
├── backend/
│   ├── main.py                  ← FastAPI routes only, no logic here
│   ├── orchestrator.py          ← top node, question classifier, controls all agents
│   ├── session.py               ← in-memory dict, exact shape defined below
│   ├── agents/
│   │   ├── index_agent.py       ← file tree, dep graph, centrality scoring
│   │   └── signal_agent.py      ← TODOs, churn, unused fields, arch violations
│   ├── mcp/
│   │   └── github_client.py     ← all GitHub MCP calls, nowhere else
│   └── llm/
│       ├── gemini_client.py     ← Gemini API wrapper
│       └── rate_queue.py        ← 15 RPM guard, retry, exponential backoff
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── UrlInput.jsx     ← URL paste, triggers index
│           ├── AutoBrief.jsx    ← 4-section brief, PRIMARY view
│           └── Chat.jsx         ← conversational interface, SECONDARY view
│
└── ARCHITECTURE.md              ← this file
```

---

## Session Store Shape (exact, do not change)

```python
session_store[session_id] = {
    "repo_meta": {
        "owner": str,
        "repo": str,
        "url": str,
        "timestamp": float
    },
    "indexed_files": {
        "filename": "content_string"
    },
    "dependency_graph": {
        "filename": ["imported_file_1", "imported_file_2"]
    },
    "signals": {
        "todos": [{"file": str, "count": int, "lines": [str]}],
        "churn": [{"file": str, "commit_count": int}],
        "unused_fields": [{"field": str, "defined_in": str, "note": str}],
        "violations": [{"file": str, "pattern": str, "violation": str}]
    },
    "brief": {
        "architecture": str,
        "core_modules": [{"file": str, "role": str, "badge": str}],
        "hidden_signals": [{"type": str, "title": str, "detail": str, "source": str}],
        "unused_data": [{"field": str, "note": str, "tag": str}]
    },
    "timestamp": float
}
```

Define this shape on day one. Never change the top-level keys. Add nested fields freely.

---

## Agent Responsibilities

| Agent | Does | Does not |
|---|---|---|
| Orchestrator | dispatches agents, classifies questions, aggregates results, calls Gemini | call GitHub MCP directly |
| Index Agent | file tree, dep graph, centrality = import_count + referenced_by_count, top 8 files | call Gemini |
| Signal Agent | TODOs, commit churn, unused schema fields, architectural violations | call Gemini |
| GitHub MCP client | all MCP tool calls, cache results to session immediately | contain business logic |
| Rate Queue | guards every Gemini call, 15 RPM, retry on 429 | know about agents |

---

## Centrality Scoring (keep simple)

```python
centrality[file] = import_count[file] + referenced_by_count[file]
```

Nothing more complex. Judges care about output quality, not graph theory.

---

## Question Classifier (inside Orchestrator, not a separate agent)

```python
def classify_question(question: str) -> str:
    # one of: "architecture" | "flow" | "drift" | "signal" | "module"
    # each type gets different Gemini prompt + different session_store keys
```

- `architecture` → pulls brief.architecture + core_modules
- `flow` → pulls indexed_files for relevant module, generates trace
- `drift` → pulls signals.violations + signals.churn
- `signal` → pulls signals.todos + signals.unused_fields
- `module` → pulls indexed_files[specific_file] + dep graph

---

## Data Flow

### Indexing (on URL paste)
```
POST /index { url }
  → parse owner/repo from URL
  → create session_id, initialise session_store shape
  → orchestrator.run(owner, repo, session_id)
  → parallel:
      index_agent.run()
        → github_client.get_file_tree()           ← cache immediately
        → github_client.get_file_contents(top 8)  ← cache immediately
        → build dep graph from imports
        → score centrality = import_count + referenced_by_count
        → write to session_store.indexed_files + dependency_graph

      signal_agent.run()
        → github_client.search_code("TODO", "FIXME", "hack")  ← cache immediately
        → github_client.list_commits(limit=30)                 ← cache immediately
        → github_client.list_issues(state="open", limit=20)   ← cache immediately
        → detect unused schema fields (schema def vs search_code usage)
        → detect architectural violations (outlier files vs dominant pattern)
        → write to session_store.signals

  → orchestrator aggregates
  → calls Gemini via rate_queue → generates brief (4 sections)
  → writes to session_store.brief
  → returns { session_id, brief }
```

### Chat (on user question)
```
POST /chat { session_id, question }
  → classify_question(question) → question_type
  → pull relevant keys from session_store (no re-fetch if already cached)
  → if specific file needed and not cached → github_client.get_file_contents()
  → build prompt based on question_type
  → call Gemini via rate_queue
  → return { answer, sources[] }
```

---

## Hidden Signal That Creates Demo Wow

Signal Agent must produce this in `signals.violations`:

```
"Most files follow middleware pattern. auth.js bypasses validation 
used by all other routes. This is the most likely source of bugs."
```

This is heuristic-based. One extra Gemini prompt reading the top 8 files.
This is the signal judges remember after the demo.

---

## UI Order (do not invert this)

```
1. URL input bar
2. Loading state (indexing)
3. AUTO-BRIEF appears first   ← primary, this is the product
4. Chat input below brief     ← secondary, for follow-up
```

Auto-brief is the product. Chat is a feature. Never let chat be the first thing a judge sees.

---

## Hard Rules (never break)

- Only Orchestrator calls Gemini
- Only GitHub MCP client calls GitHub
- Cache every MCP fetch to session_store immediately — never fetch same file twice
- No database — session store is a Python dict
- No vector DB, no embeddings, no graph visualization library
- No auth — public repos only
- Rate queue is mandatory on every Gemini call
- Agents are stateless — inputs in, outputs out, session write only

---

## GitHub MCP Setup

```bash
npm install -g @modelcontextprotocol/server-github
GITHUB_TOKEN=ghp_xxxx npx @modelcontextprotocol/server-github
# Token scope: public_repo read-only
# Add to .env: GITHUB_TOKEN=ghp_xxxx, GEMINI_API_KEY=xxx
```

---

## Gemini Setup

```
Model:  gemini-2.0-flash-lite
Limits: 15 RPM · 1500 RPD · 1M token context
Key:    GEMINI_API_KEY in .env
Rule:   every call goes through rate_queue.call()
```

---

## Demo Repo (test before demo, pick the best output)

Good choices:
- `expressjs/express` — clean arch, real TODOs, medium size
- `fastapi/fastapi` — ironic, clean structure
- A public indie hacker repo with visible drift

Avoid anything over 200 files. Demo clarity beats technical complexity.

---

## IDE Handoff

- **Antigravity:** primary
- **Emergent:** fallback on token limit
- **On shift:** first message = "Read ARCHITECTURE.md. Then read orchestrator.py. Current task: [next task below]."
- **Memory MCP:** add after MVP ships, not before

---

## Current State

```
Status: [ ] not started  [ ] in progress  [x] done

[x] FastAPI skeleton — server.py, /api/index and /api/chat routes
[x] Session store — session.py with exact shape
[x] GitHub client — github_client.py (REST), all 5 tool calls, cached
[x] Rate queue — rate_queue.py, 15 RPM guard
[x] LLM client — llm_client.py (Claude Sonnet 4.5 via Emergent Universal Key)
[x] Index Agent — index_agent.py
[x] Signal Agent — signal_agent.py, including violations signal
[x] Orchestrator — orchestrator.py, question classifier included
[x] Auto-brief assembly — 4 sections from session_store.brief
[x] React URL input — UrlInput.jsx
[x] React auto-brief — AutoBrief.jsx
[x] React chat — Chat.jsx
[x] Phase 6 polish — ErrorBoundary, RepoSizeBanner (>200 files), default-branch detection
[x] Counter — /api/stats + persistent JSON counter + landing chip
[x] Lifespan ctx manager replacing deprecated @app.on_event
[x] Production build served by `yarn start` (no HMR — avoids reload-on-disconnect loops behind reverse proxies)
```

**LLM provider:** Claude Sonnet 4.5 (`anthropic/claude-sonnet-4-5-20250929`) via
the Emergent Universal Key — replacing Gemini 2.0 Flash Lite in earlier phases.

**In progress:** nothing — Phase 6 polish complete.

**Last decision:** switched frontend from Vite dev server to a production build
+ `vite preview` to eliminate HMR-WebSocket-driven reload loops when served
behind a reverse proxy / K8s ingress.

**Next task:** demo dry-runs against `expressjs/express` and `fastapi/fastapi`
to verify the "outlier bypasses dominant pattern" wow violation surfaces.

**Do not touch:** session_store top-level keys, the "only Orchestrator calls
the LLM" rule, the "only github_client calls GitHub" rule, the UI order
(URL input → loading → AutoBrief → Chat).