# RepoChat

**RepoChat** is a codebase comprehension layer for the AI coding era. Paste any public GitHub URL — before you ask a single question, RepoChat automatically analyzes the repository and generates a plain-English brief explaining how the system is structured, which modules matter most, where architectural drift exists, and what hidden risks are accumulating.

> **Core insight:** AI made development cheap. Clarity became expensive. RepoChat restores it.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | FastAPI skeleton, session store, React stubs | ✅ Complete |
| Phase 2 | GitHub REST client, 15 RPM rate queue, LLM client | ✅ Complete |
| Phase 3 | Index Agent, Signal Agent | ✅ Complete |
| Phase 4 | Orchestrator, question classifier, real brief generation | ✅ Complete |
| Phase 5 | React frontend (URL input → auto-brief → chat) | ⏳ Next |
| Phase 6 | Polish, error handling, demo prep | ⏳ Upcoming |

## What It Does

1. **Paste a GitHub URL** — any public repo
2. **Auto-Brief appears** — 4 sections generated before you ask anything:
   - Architecture summary (how the system is built)
   - Core modules (top 8 files by centrality score)
   - Hidden signals (violations, TODO clusters, high-churn files)
   - Unused data (schema fields defined but never referenced)
3. **Ask questions** — conversational Q&A with source citations:
   - *"How is this architecture structured?"* → architecture mode
   - *"How does a request flow through the system?"* → flow mode
   - *"What changed recently?"* → drift mode
   - *"What are the TODOs and hidden risks?"* → signal mode
   - *"What does middleware.js do?"* → module mode

## Architecture

```
React (Vite) · localhost:3000
      ↓ HTTP
FastAPI · localhost:8000
      ↓
Orchestrator          ← only node that calls LLM
      ↓ asyncio.gather
Index Agent    Signal Agent
      ↓               ↓
      └── GitHub REST API ──┘
               ↓
    Gemini 2.0 Flash Lite (via OpenRouter)
               ↓
       Rate Limit Queue (15 RPM)
```

**Agent responsibilities:**

| Agent | Does | Does not |
|-------|------|----------|
| Orchestrator | dispatches agents, classifies questions, calls LLM, builds brief | call GitHub directly |
| Index Agent | file tree, dep graph, centrality scoring, top 8 files | call LLM |
| Signal Agent | TODOs, commit churn, unused fields, arch violations | call LLM |
| GitHub client | all REST API calls, caches results immediately | contain business logic |
| Rate Queue | 15 RPM guard, retry on 429, exponential backoff | know about agents |

**Question classifier** (keyword-based, no LLM cost):
- `architecture` → pulls `brief.architecture` + `core_modules`
- `flow` → pulls `indexed_files` + dependency graph
- `drift` → pulls `signals.violations` + `signals.churn`
- `signal` → pulls `signals.todos` + `signals.unused_fields`
- `module` → pulls `indexed_files[file]` + dep graph

## Stack

- **Backend:** FastAPI + Python 3.11
- **Frontend:** React + Vite
- **LLM:** Gemini 2.0 Flash Lite via OpenRouter
- **GitHub data:** GitHub REST API v3 (authenticated, 5000 req/hour)
- **Session store:** In-memory Python dict (no database)

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A GitHub personal access token (`public_repo` scope)
- An OpenRouter API key (free tier available at openrouter.ai)

### Backend

```bash
# From project root
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your keys:
#   GITHUB_TOKEN=ghp_...
#   OPENROUTER_API_KEY=sk-or-v1-...

# Start the server (run from backend/ directory)
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs at localhost:3000
```

### Test the API directly

```bash
# Index a repo
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/expressjs/express"}'

# Chat (use session_id from above response)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "question": "How is this architecture structured?"}'
```

## Hard Rules (never break)

- Only `orchestrator.py` calls the LLM
- Only `mcp/github_client.py` calls GitHub
- Cache every GitHub fetch to session store — never fetch the same file twice
- No database — session store is a Python dict
- No vector DB, no embeddings
- No auth — public repos only
- Rate queue is mandatory on every LLM call

---

*Built by [Himanshu](https://github.com/productbyhimanshu)*
