# Repochat

**Repochat** is an AI-powered GitHub repository chat and QA tool. By simply pasting a public GitHub repository URL, Repochat analyzes the repository's architecture, dependencies, and code signals to generate an instant briefing, followed by a conversational interface to dive deep into the codebase.

## 🚀 Features

- **Instant Auto-Brief**: Automatically generates a 4-section summary of any repository:
  1. Architecture summary
  2. Core modules (extracted via centrality scoring)
  3. Hidden signals (TODOs, commit churn, unused fields, and architectural violations)
  4. Unused data detection
- **Intelligent Indexing**: Calculates a `centrality score` based on the dependency graph (`import_count + referenced_by_count`) to identify the most critical files in a project.
- **GitHub MCP Integration**: Uses the `@modelcontextprotocol/server-github` to directly interact with GitHub (file tree, code search, commit history) and safely caches every response.
- **Gemini-Powered Q&A**: Employs `gemini-2.0-flash-lite` wrapped inside a robust 15 RPM Rate Queue that automatically handles 429 backoffs.

## 🏗 Architecture

**Stack**:
- **Frontend**: React + Vite (State machine: idle → loading → brief_ready)
- **Backend**: FastAPI (Python)
- **AI/LLM**: Google Gemini (`gemini-2.0-flash-lite`)
- **Integration**: GitHub Model Context Protocol (MCP) Server

**Core Agents**:
1. **Orchestrator**: Routes user questions to appropriate contexts (architecture, flow, drift, signal, module).
2. **Index Agent**: Parses the file tree, builds the dependency graph, calculates centrality, and stores the top 8 core modules.
3. **Signal Agent**: Performs heuristic searches to detect technical debt, TODOs, and architectural violations (the "Wow" signal).

## 🏁 Current Status

- **Phase 1 (Foundation)**: Complete ✅ (FastAPI skeleton, React stubs, rigid session store shape)
- **Phase 2 (GitHub MCP + LLM)**: Complete ✅ (MCP tools, 15 RPM Rate Queue, Gemini Client)
- **Phase 3 (Agents)**: Complete ✅ (Index Agent & Signal Agent operational)
- **Phase 4 (Orchestrator)**: In Progress ⏳
- **Phase 5 (React UI)**: Not started
- **Phase 6 (Polish)**: Not started

## 🛠 Setup & Development

1. Clone the repository and install backend dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Install the GitHub MCP Server globally:
   ```bash
   npm install -g @modelcontextprotocol/server-github
   ```

3. Configure your `.env` file:
   ```env
   GITHUB_TOKEN=ghp_your_github_token
   GEMINI_API_KEY=AIza...your_gemini_key
   ```

4. Start the backend:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

5. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---
*Developed by Himanshu.*
