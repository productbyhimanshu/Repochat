/**
 * App.jsx — Root state machine for Repochat.
 *
 * States: idle → loading → brief_ready
 * Render order (never invert):
 *   1. UrlInput  (idle)
 *   2. Loading   (loading)
 *   3. AutoBrief (brief_ready)  ← PRIMARY view
 *   4. Chat      (brief_ready)  ← SECONDARY view, always below brief
 *
 * Phase 1: wired to real /index and /chat endpoints,
 *          but endpoints return mock data until Phase 4.
 */

import { useState } from "react";
import UrlInput  from "./components/UrlInput.jsx";
import AutoBrief from "./components/AutoBrief.jsx";
import Chat      from "./components/Chat.jsx";

const API_BASE = "";   // Vite proxy handles /index and /chat

export default function App() {
  const [appState,  setAppState]  = useState("idle");   // idle | loading | brief_ready
  const [sessionId, setSessionId] = useState(null);
  const [brief,     setBrief]     = useState(null);
  const [error,     setError]     = useState(null);

  // ── handlers ──────────────────────────────────────────────────────────────

  async function handleUrlSubmit(url) {
    setError(null);
    setAppState("loading");

    try {
      const res = await fetch(`${API_BASE}/index`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ url }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      setSessionId(data.session_id);
      setBrief(data.brief);
      setAppState("brief_ready");
    } catch (err) {
      setError(err.message);
      setAppState("idle");
    }
  }

  // ── render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: "100vh", background: "#0d1117", color: "#e6edf3", fontFamily: "system-ui, sans-serif" }}>
      {/* Step 1 — URL input (always visible at top) */}
      {appState === "idle" && (
        <UrlInput onSubmit={handleUrlSubmit} error={error} />
      )}

      {/* Step 2 — Loading */}
      {appState === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
          <p style={{ fontSize: 18, color: "#8b949e" }}>Indexing repository…</p>
          <p style={{ fontSize: 13, color: "#484f58" }}>This may take a few seconds</p>
        </div>
      )}

      {/* Step 3+4 — Brief then Chat (order locked) */}
      {appState === "brief_ready" && (
        <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 20px" }}>
          <AutoBrief brief={brief} />
          <Chat sessionId={sessionId} />
        </div>
      )}
    </div>
  );
}
