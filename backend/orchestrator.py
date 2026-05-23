"""
orchestrator.py — Top node. Only this module calls Gemini.

Responsibilities:
  - Dispatch Index Agent and Signal Agent in parallel
  - Generate the 4-section auto-brief via Gemini
  - Classify chat questions and build context-aware answers
"""

import asyncio
import json

from agents import index_agent, signal_agent
from llm.llm_client import generate
from session import require_session
from logger import get_logger

log = get_logger("repochat.orchestrator")


# ── Question Classifier ─────────────────────────────────────────────────────────

def classify_question(question: str) -> str:
    """
    Classify into: architecture | flow | drift | signal | module
    Keyword-based — fast, no LLM needed.
    """
    q = question.lower()

    if any(w in q for w in ["drift", "changed", "recent", "unstable", "broken", "regressed", "churn"]):
        return "drift"
    if any(w in q for w in ["flow", "through", "trace", "path", "request", "response", "moves", "travels", "pipeline"]):
        return "flow"
    if any(w in q for w in ["todo", "fixme", "hack", "unused", "signal", "risk", "hidden", "warning", "issue"]):
        return "signal"
    if any(w in q for w in ["file", "module", "class", "function", "method", "purpose", "explain", "what does", "how does"]):
        return "module"
    return "architecture"


# ── Brief Generation ────────────────────────────────────────────────────────────

async def run(owner: str, repo: str, session_id: str) -> dict:
    """
    Dispatch agents in parallel, then generate the 4-section brief via Gemini.
    Returns the brief dict and writes it to session_store.brief.
    """
    log.agent("orchestrator", f"Starting for {owner}/{repo}")
    store = require_session(session_id)

    # 1. Run both agents in parallel
    await asyncio.gather(
        index_agent.run(owner, repo, session_id),
        signal_agent.run(owner, repo, session_id),
    )
    log.agent("orchestrator", "Both agents complete — generating brief")

    # 2. Pull data from session store
    indexed = store["indexed_files"]
    dep_graph = store["dependency_graph"]
    signals = store["signals"]

    # Truncate file contents to stay within token budget
    files_block = "\n\n".join(
        f"### {fname}\n```\n{content[:1200]}\n```"
        for fname, content in list(indexed.items())[:8]
    ) or "(no source files indexed)"

    violations_block = "\n".join(
        f"- [{v['file']}] {v['violation']}"
        for v in signals["violations"]
    ) or "None detected"

    todos_block = "\n".join(
        f"- {t['file']}: {t['lines'][0] if t['lines'] else 'TODO found'}"
        for t in signals["todos"][:6]
    ) or "None detected"

    churn_block = "\n".join(
        f"- {c['file']} ({c['commit_count']} recent commits)"
        for c in signals["churn"][:5]
    ) or "None detected"

    unused_block = "\n".join(
        f"- `{u['field']}` in {u['defined_in']}: {u['note']}"
        for u in signals["unused_fields"][:5]
    ) or "None detected"

    top_files = list(indexed.keys())[:8]

    # 3. Call Gemini for brief
    prompt = f"""You are a senior software architect analyzing the GitHub repository: {owner}/{repo}.

## Top Source Files
{files_block}

## Architectural Violations Detected
{violations_block}

## TODOs / FIXMEs Found
{todos_block}

## High-Churn Files
{churn_block}

## Potentially Unused Schema Fields
{unused_block}

Generate a JSON object with EXACTLY this structure and no other text:
{{
  "architecture": "<2-3 sentence plain-English summary of what this system does and how it is structured>",
  "core_modules": [
    {{"file": "<path>", "role": "<one-sentence description>", "badge": "<Core|Router|Util|Config|Auth|API|DB|CLI>"}}
  ],
  "hidden_signals": [
    {{"type": "<violation|todo|churn>", "title": "<short title>", "detail": "<plain-English explanation>", "source": "<filename>"}}
  ],
  "unused_data": [
    {{"field": "<field_name>", "note": "<why it appears unused>", "tag": "<Stale|Orphaned|Legacy>"}}
  ]
}}

Rules:
- core_modules must include all of these files (one entry each): {json.dumps(top_files)}
- hidden_signals: convert violations, top TODOs, and top churn files into readable insight cards
- unused_data: list all unused fields found above
- Be specific — cite real file names and real patterns
- Return ONLY the JSON object, no markdown fences, no extra explanation"""

    log.agent("orchestrator", "Calling Gemini for brief")
    raw = await generate(prompt)

    brief = _parse_json_response(raw, fallback=_fallback_brief(owner, repo, indexed, signals))

    # 4. Persist to session
    store["brief"].update(brief)
    log.agent("orchestrator", "Brief written to session_store.brief")
    return brief


# ── Chat Answer ─────────────────────────────────────────────────────────────────

async def answer_question(session_id: str, question: str) -> dict:
    """
    Classify question → pull relevant session context → call Gemini → return answer + sources.
    """
    store = require_session(session_id)
    owner = store["repo_meta"]["owner"]
    repo = store["repo_meta"]["repo"]

    q_type = classify_question(question)
    log.agent("orchestrator", f"Question classified as '{q_type}': {question!r}")

    context, sources = _build_context(store, q_type, question)

    prompt = f"""You are an expert software architect answering a question about the GitHub repository: {owner}/{repo}.

Question type: {q_type}
Question: {question}

Repository context:
{context}

Answer in plain English. Be specific — cite real file names from the context.
Keep the response under 350 words.
Structure the answer clearly (short paragraphs or a brief list where appropriate).
Do not invent details that are not in the context."""

    log.agent("orchestrator", "Calling Gemini for chat answer")
    answer = await generate(prompt)

    unique_sources = list(dict.fromkeys(s for s in sources if s))
    return {"answer": answer, "sources": unique_sources}


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _build_context(store: dict, q_type: str, question: str) -> tuple:
    """Return (context_string, sources_list) for the given question type."""
    indexed = store["indexed_files"]
    dep_graph = store["dependency_graph"]
    signals = store["signals"]
    brief = store["brief"]
    sources: list = []

    if q_type == "architecture":
        lines = [f"Architecture Summary: {brief.get('architecture', '')}",
                 "", "Core Modules:"]
        for m in brief.get("core_modules", []):
            lines.append(f"  - {m['file']}: {m['role']} [{m['badge']}]")
            sources.append(m["file"])
        context = "\n".join(lines)

    elif q_type == "flow":
        parts = ["Source files for flow analysis:\n"]
        for fname, content in list(indexed.items())[:5]:
            parts.append(f"### {fname}\n```\n{content[:700]}\n```")
            sources.append(fname)
        deps_snippet = json.dumps(
            {k: v for k, v in list(dep_graph.items())[:10]}, indent=2
        )
        parts.append(f"\nDependency graph (excerpt):\n{deps_snippet[:600]}")
        context = "\n\n".join(parts)

    elif q_type == "drift":
        lines = ["Architectural Violations:"]
        for v in signals["violations"]:
            lines.append(f"  - [{v['file']}] {v['violation']}")
            sources.append(v["file"])
        lines.append("\nHigh-Churn Files:")
        for c in signals["churn"]:
            lines.append(f"  - {c['file']}: {c['commit_count']} recent commits")
            sources.append(c["file"])
        context = "\n".join(lines)

    elif q_type == "signal":
        lines = ["TODOs / FIXMEs:"]
        for t in signals["todos"]:
            snippet = t["lines"][0] if t.get("lines") else "TODO found"
            lines.append(f"  - {t['file']}: {snippet}")
            sources.append(t["file"])
        lines.append("\nPotentially Unused Fields:")
        for u in signals["unused_fields"]:
            lines.append(f"  - `{u['field']}` in {u['defined_in']}: {u['note']}")
            sources.append(u["defined_in"])
        context = "\n".join(lines)

    else:  # module
        q_lower = question.lower()
        best = next(
            (f for f in indexed if any(w in f.lower() for w in q_lower.split())),
            next(iter(indexed), None),
        )
        if best:
            context = (
                f"### {best}\n```\n{indexed[best][:2000]}\n```\n\n"
                f"Dependencies: {json.dumps(dep_graph.get(best, []))}"
            )
            sources.append(best)
        else:
            context = "No specific module found in session. Falling back to architecture overview.\n\n" + brief.get("architecture", "")

    return context, sources


def _parse_json_response(raw: str, fallback: dict) -> dict:
    """Strip markdown fences and parse JSON from Gemini response."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as exc:
        log.api_error("orchestrator.parse_json", error=str(exc))
        return fallback


def _fallback_brief(owner: str, repo: str, indexed: dict, signals: dict) -> dict:
    """Return a minimal brief when Gemini parsing fails."""
    return {
        "architecture": f"{owner}/{repo} — architecture analysis encountered a parsing issue. The repository has been indexed successfully.",
        "core_modules": [
            {"file": f, "role": "Source file", "badge": "Core"}
            for f in list(indexed.keys())[:4]
        ],
        "hidden_signals": [
            {
                "type": v["type"] if "type" in v else "violation",
                "title": "Signal detected",
                "detail": v.get("violation", str(v)),
                "source": v.get("file", "unknown"),
            }
            for v in signals.get("violations", [])[:2]
        ],
        "unused_data": [
            {"field": u["field"], "note": u["note"], "tag": "Stale"}
            for u in signals.get("unused_fields", [])[:3]
        ],
    }
