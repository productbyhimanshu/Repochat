# Repochat — Project TODO

> **Rule:** Never break the Hard Rules in `architeture.md`. Each phase builds on the one before it. Do not start a phase until the prior phase's tests pass.

---

## Phase 1 — Foundation & Infrastructure
> **Goal:** Skeleton is up, environment is wired, no real logic yet.
> **Unblocks:** All other phases depend on this.

### Setup
- [x] Create `.env` with `GITHUB_TOKEN` and `GEMINI_API_KEY`
- [x] Create `backend/` directory structure:
  ```
  backend/
  ├── main.py
  ├── session.py
  ├── agents/
  ├── mcp/
  └── llm/
  ```
- [x] Create `frontend/src/` directory with `App.jsx` and `components/`
- [x] Add `requirements.txt` (fastapi, uvicorn, httpx, python-dotenv, google-generativeai)
- [x] Add `package.json` for frontend (React + Vite)

### Backend Skeleton
- [x] `backend/main.py` — FastAPI app, `/index` POST and `/chat` POST routes returning **hardcoded mock JSON**
- [x] `backend/session.py` — define `session_store` dict with the **exact shape** from `architeture.md` (top-level keys locked: `repo_meta`, `indexed_files`, `dependency_graph`, `signals`, `brief`, `timestamp`)

### ✅ Phase 1 Tests — ALL PASSED ✓
- [x] `uvicorn main:app` starts without errors
- [x] `POST /index { "url": "..." }` returns mock `{ session_id, brief }`
- [x] `POST /chat { "session_id": "...", "question": "..." }` returns mock `{ answer, sources }`
- [x] Session store shape matches spec exactly — verify keys manually

---

## Phase 2 — GitHub MCP Client + Rate Queue
> **Goal:** Real GitHub data flows in; every Gemini call is rate-guarded.
> **Depends on:** Phase 1 (session store shape, FastAPI skeleton)

### GitHub MCP Client (`backend/mcp/github_client.py`)
- [x] Install `@modelcontextprotocol/server-github` globally
- [x] Implement all 5 MCP tool calls:
  - [x] `get_file_tree(owner, repo)` → returns file list
  - [x] `get_file_contents(owner, repo, path)` → returns file string
  - [x] `search_code(owner, repo, query)` → for TODO/FIXME/hack
  - [x] `list_commits(owner, repo, limit=30)` → commit list
  - [x] `list_issues(owner, repo, state, limit)` → issue list
- [x] **Cache every result to `session_store` immediately** after fetch — never re-fetch same file

### Rate Queue (`backend/llm/rate_queue.py`)
- [x] Implement 15 RPM guard with a token-bucket or sliding window
- [x] Retry on HTTP 429 with exponential backoff
- [x] Expose a single `call(fn, *args, **kwargs)` interface — all Gemini calls go through here

### Gemini Client (`backend/llm/gemini_client.py`)
- [x] Wrap `gemini-2.0-flash-lite` API
- [x] Single `generate(prompt: str) → str` method
- [x] **All calls must go through `rate_queue.call()`** — enforce this here, not at call site

### ✅ Phase 2 Tests — ALL PASSED ✓
- [x] Call `github_client.get_file_tree("expressjs", "express")` — returns file list
- [x] Call same endpoint twice — verify second call hits cache (no MCP call made)
- [x] Fire 16 Gemini requests in 1 minute — verify 16th is queued, not dropped
- [x] 429 response → retry fires with backoff

---

## Phase 3 — Index Agent + Signal Agent
> **Goal:** Real repo intelligence is extracted and written to session store.
> **Depends on:** Phase 2 (GitHub MCP client + Rate Queue must be working)

### Index Agent (`backend/agents/index_agent.py`)
- [x] Fetch file tree via `github_client`
- [x] Fetch top-8 files by centrality (see scoring below)
- [x] Build dependency graph: `{ filename: [imported_file_1, ...] }`
- [x] Score centrality: `centrality[file] = import_count[file] + referenced_by_count[file]`
- [x] Write `indexed_files` and `dependency_graph` to `session_store`
- [x] Agent is **stateless**: inputs in, outputs out + session write only

### Signal Agent (`backend/agents/signal_agent.py`)
- [x] Search code for `TODO`, `FIXME`, `hack` → write to `signals.todos`
- [x] List 30 commits, rank by file churn → write to `signals.churn`
- [x] Detect unused schema fields (def vs usage search) → write to `signals.unused_fields`
- [x] Detect architectural violations (outlier files vs dominant pattern) → write to `signals.violations`
- [x] **Violations must produce the "wow" signal**: one Gemini prompt reading top 8 files, identifying the outlier bypassing the dominant pattern
- [x] Agent is **stateless**: inputs in, outputs out + session write only

### ✅ Phase 3 Tests — ALL PASSED ✓
- [x] Run both agents on `expressjs/express` — all `session_store` keys populated
- [x] `signals.violations` contains at least one entry with file, pattern, and violation text
- [x] Centrality scores are non-zero and top-8 files are plausible (index/router/main)
- [x] Same MCP call not made twice (cache verified)
- [x] Both agents run in parallel without race condition on `session_store`

---

## Phase 4 — Orchestrator + Question Classifier
> **Goal:** Orchestrator ties agents together, classifies questions, builds Gemini prompts.
> **Depends on:** Phase 3 (both agents must write correct data to session store)

### Orchestrator (`backend/agents/orchestrator.py`)
- [ ] `run(owner, repo, session_id)` — dispatch Index Agent and Signal Agent **in parallel** (use `asyncio.gather`)
- [ ] Aggregate results once both agents complete
- [ ] Call Gemini via `rate_queue` to generate 4-section brief:
  - `architecture` (summary of structure)
  - `core_modules` (top 8 files with role + badge)
  - `hidden_signals` (violations, churn, todos as insight cards)
  - `unused_data` (unused schema fields)
- [ ] Write completed brief to `session_store.brief`
- [ ] **Only Orchestrator calls Gemini** — enforce this rule

### Question Classifier (inside `orchestrator.py`)
- [ ] `classify_question(question: str) → str` — returns one of: `architecture | flow | drift | signal | module`
- [ ] Each type maps to different session_store keys and Gemini prompt template:
  - `architecture` → `brief.architecture` + `core_modules`
  - `flow` → `indexed_files` for relevant module
  - `drift` → `signals.violations` + `signals.churn`
  - `signal` → `signals.todos` + `signals.unused_fields`
  - `module` → `indexed_files[file]` + `dependency_graph`
- [ ] Wire `/chat` route in `main.py` to use classifier → build prompt → call Gemini → return `{ answer, sources[] }`
- [ ] `/index` route now calls `orchestrator.run()` (replace mock)

### ✅ Phase 4 Tests
- [ ] `POST /index` with `expressjs/express` → real brief returned (not mock)
- [ ] `brief` has all 4 sections with non-empty content
- [ ] Ask 5 different question types — classifier returns correct type for each
- [ ] `POST /chat` with a drift question → answer references `signals.violations`
- [ ] No agent calls GitHub MCP directly (only `github_client.py` may)
- [ ] No agent calls Gemini directly (only `orchestrator.py` may)

---

## Phase 5 — React Frontend
> **Goal:** Working UI in correct order — URL input → loading → auto-brief → chat.
> **Depends on:** Phase 4 (backend `/index` and `/chat` must return real data)

### `frontend/src/App.jsx`
- [x] State machine: `idle → loading → brief_ready`
- [x] Renders `<UrlInput>` in `idle` state
- [x] Renders loading indicator during `loading`
- [x] Renders `<AutoBrief>` then `<Chat>` in `brief_ready` (this order, never inverted)
- [x] Stores `session_id` in state for chat calls

### `frontend/src/components/UrlInput.jsx`
- [x] Text input for GitHub repo URL
- [x] On submit: `POST /api/index { url }` → transitions to loading
- [x] Show inline error if URL invalid or backend errors
- [x] Shareability counter chip ("X repos understood")

### `frontend/src/components/AutoBrief.jsx`
- [x] Renders all 4 brief sections:
  - Architecture summary (text card)
  - Core modules (file list with role + badge, links to GitHub)
  - Hidden signals (insight cards from `hidden_signals`)
  - Unused data (field list with tags)
- [x] **Primary view — designed to impress first**

### `frontend/src/components/Chat.jsx`
- [x] Chat input at bottom of page (below auto-brief)
- [x] On submit: `POST /api/chat { session_id, question }` → render answer
- [x] Show `sources[]` as clickable file references (deep-linked to GitHub)
- [x] Markdown rendering via `react-markdown` + `remark-gfm`

### ✅ Phase 5 Tests — ALL PASSED
- [x] Paste `https://github.com/expressjs/express` → loading shows → brief appears
- [x] Brief has all 4 sections with real data
- [x] Chat input only visible **after** brief loads
- [x] Ask "what are the TODOs?" → correct answer from signals
- [x] Ask "explain the middleware flow" → classified as `flow`, correct answer
- [x] No full-page reload on any action

---

## Phase 6 — Polish, Error Handling & Demo Prep
> **Goal:** System is demo-ready. Edge cases handled. Wow signal confirmed.
> **Depends on:** Phase 5 (full stack working end-to-end)

### Hardening
- [x] Add error boundaries in React — no blank screen on API failure
- [x] Backend: return structured `{ detail }` on all failure paths
- [x] Handle repos with 0 TODOs, 0 violations gracefully (empty states in UI)
- [x] Validate GitHub URL format before calling `/api/index`
- [x] Enforce 200-file limit: warn user if repo is too large (`RepoSizeBanner`)
- [x] Migrate `@app.on_event` → lifespan context manager
- [x] Detect repo default branch in `fileUrl()` (was hard-coded `HEAD`)
- [x] Persistent `/api/stats` counter + landing "X repos understood" chip
- [x] Switched frontend from Vite dev to production build + preview (no HMR =
  no reload-on-disconnect loops behind reverse proxies)

### Demo Prep
- [ ] Test against `expressjs/express` end-to-end — verify wow signal in violations
- [ ] Test against `fastapi/fastapi` — verify brief is accurate
- [ ] Confirm `signals.violations` produces the "outlier bypasses dominant pattern" insight
- [x] Confirm auto-brief loads in < 60 seconds for medium repos
- [x] Confirm chat responds in < 15 seconds (no re-fetch from cache)

### Final Checks (Hard Rules Audit)
- [x] Only Orchestrator calls the LLM ✓
- [x] Only `github_client.py` calls GitHub ✓
- [x] Cache verified — no double-fetches ✓
- [x] No database, no vector DB, no embeddings ✓
- [x] No auth — only public repos ✓
- [x] Rate queue active on every LLM call ✓
- [x] Session store top-level keys unchanged ✓

### ✅ Phase 6 Tests
- [x] Backend 11/11 pytest pass: health, stats, /index valid + 422, /chat 200 + 404 + 422,
      all 5 classifier kinds, default_branch=master for commander.js, total_files>200,
      counter increment = before + 1
- [x] Frontend 100% on tested flows: stats-counter visible, repo-size-banner at 223 files,
      module hrefs use `/blob/master/`, ErrorBoundary invisible on happy path
- [ ] Final demo dry-runs on `expressjs/express` + `fastapi/fastapi`
- [ ] Rate limit stress test: index 3 repos in sequence — no 429 errors leak to UI
- [x] `.env` has both keys set; app logs warning if keys missing

---

## Dependency Map

```
Phase 1 (Foundation)
    └── Phase 2 (GitHub MCP + Rate Queue)
            └── Phase 3 (Index Agent + Signal Agent)
                    └── Phase 4 (Orchestrator + Classifier)
                            └── Phase 5 (React Frontend)
                                    └── Phase 6 (Polish + Demo)
```

**Never skip a phase. Each phase's tests must pass before the next begins.**
