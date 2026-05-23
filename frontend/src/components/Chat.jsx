/**
 * Chat.jsx — Conversational Q&A interface.
 *
 * Phase 1 stub: sends questions to POST /chat,
 * renders mock answers below AutoBrief.
 * Full design and streaming in Phase 5.
 */

import { useState } from "react";

export default function Chat({ sessionId }) {
  const [question, setQuestion]   = useState("");
  const [messages, setMessages]   = useState([]);
  const [loading,  setLoading]    = useState(false);
  const [error,    setError]      = useState(null);

  async function handleAsk(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    setMessages(prev => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/chat", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ session_id: sessionId, question: q }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      setMessages(prev => [...prev, {
        role:    "assistant",
        text:    data.answer,
        sources: data.sources || [],
      }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div id="chat-panel">
      <h2 style={{ fontSize: 18, color: "#e6edf3", marginBottom: 16 }}>Ask a question</h2>

      {/* Message history */}
      <div id="chat-messages" style={{ marginBottom: 20 }}>
        {messages.map((msg, i) => (
          <div key={i} style={msg.role === "user" ? userBubble : assistantBubble}>
            <p style={{ margin: 0, lineHeight: 1.7 }}>{msg.text}</p>
            {msg.sources?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {msg.sources.map((src, j) => (
                  <span key={j} style={sourceTag}>{src}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ color: "#8b949e", fontSize: 14, padding: "8px 0" }}>Thinking…</div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleAsk} style={{ display: "flex", gap: 12 }}>
        <input
          id="chat-input"
          type="text"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="Ask anything about this repo…"
          disabled={loading}
          style={{
            flex: 1,
            padding: "12px 16px",
            borderRadius: 8,
            border: "1px solid #30363d",
            background: "#161b22",
            color: "#e6edf3",
            fontSize: 14,
            outline: "none",
          }}
        />
        <button
          id="chat-send-btn"
          type="submit"
          disabled={loading || !question.trim()}
          style={{
            padding: "12px 20px",
            borderRadius: 8,
            border: "none",
            background: loading ? "#21262d" : "#1f6feb",
            color: "#fff",
            fontSize: 14,
            cursor: loading ? "default" : "pointer",
          }}
        >
          Send
        </button>
      </form>

      {error && (
        <p id="chat-error" style={{ color: "#f85149", fontSize: 13, marginTop: 10 }}>{error}</p>
      )}
    </div>
  );
}

// ── inline styles ─────────────────────────────────────────────────────────────

const userBubble = {
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 8,
  padding: "12px 16px",
  marginBottom: 10,
  color: "#e6edf3",
  fontSize: 14,
};

const assistantBubble = {
  background: "#0d1117",
  border: "1px solid #1f6feb",
  borderRadius: 8,
  padding: "12px 16px",
  marginBottom: 10,
  color: "#c9d1d9",
  fontSize: 14,
};

const sourceTag = {
  display: "inline-block",
  marginRight: 6,
  fontSize: 11,
  color: "#79c0ff",
  background: "#0d2149",
  borderRadius: 4,
  padding: "2px 8px",
  fontFamily: "monospace",
};
