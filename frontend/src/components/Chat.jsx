/**
 * Chat.jsx — Conversational Q&A panel, always rendered BELOW AutoBrief.
 *
 * Features:
 *   - Suggested prompts (architecture / flow / drift / signal / module)
 *   - Markdown answers via react-markdown
 *   - Source chips link directly to files on GitHub
 *   - Disables input while a question is in-flight
 */

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, MessageSquareText } from "lucide-react";
import { api, fileUrl } from "../lib/api.js";

const SUGGESTED = [
  { q: "How is this architecture structured?",           tag: "architecture" },
  { q: "How does a request flow through the system?",    tag: "flow" },
  { q: "What changed recently? Where is the drift?",     tag: "drift" },
  { q: "What TODOs and hidden risks exist?",             tag: "signal" },
];

export default function Chat({ sessionId, repoMeta }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, loading]);

  async function ask(q) {
    if (!q.trim() || loading || !sessionId) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    setError(null);
    try {
      const data = await api.chat(sessionId, q);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.answer || "(no answer)", sources: data.sources || [] },
      ]);
    } catch (err) {
      setError(err.message || "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    ask(question);
  }

  return (
    <section className="chat-section" data-testid="chat-panel">
      <div className="chat-header">
        <span className="chat-eyebrow">02 · conversation</span>
      </div>
      <h2 className="chat-headline">
        Now ask anything <em>about your repo</em>
      </h2>

      {messages.length === 0 && (
        <div className="chat-prompts" data-testid="chat-prompts">
          {SUGGESTED.map((s, i) => (
            <button
              key={s.tag}
              className="chat-prompt-chip"
              onClick={() => ask(s.q)}
              type="button"
              data-testid={`chat-prompt-${s.tag}`}
              disabled={loading}
            >
              <MessageSquareText size={11} style={{ marginRight: 6, verticalAlign: -1 }} />
              {s.q}
            </button>
          ))}
        </div>
      )}

      <div className="chat-stream" data-testid="chat-stream">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`msg msg-${m.role === "user" ? "user" : "system"}`}
            data-testid={`msg-${m.role}-${i}`}
          >
            <div className="msg-meta">
              <span className="role-pill">{m.role === "user" ? "you" : "repochat"}</span>
            </div>
            <div className="msg-bubble">
              {m.role === "user" ? (
                <p style={{ margin: 0 }}>{m.text}</p>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
              )}
            </div>
            {m.sources?.length > 0 && (
              <div className="msg-sources" data-testid={`msg-sources-${i}`}>
                {m.sources.map((src) => (
                  <a
                    key={src}
                    className="src-chip"
                    href={fileUrl(repoMeta, src)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {src}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="thinking" data-testid="chat-thinking">
            <span className="dot" /><span className="dot" /><span className="dot" />
            <span style={{ marginLeft: 4 }}>reading the repo · composing answer</span>
          </div>
        )}
        <div ref={streamRef} />
      </div>

      <form className="chat-form" onSubmit={handleSubmit} data-testid="chat-form">
        <div className="chat-input-wrap">
          <input
            className="input"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask: how does data flow? what does X do? what is unstable?"
            disabled={loading}
            data-testid="chat-input"
          />
        </div>
        <button
          className="btn btn-primary"
          type="submit"
          disabled={loading || !question.trim()}
          data-testid="chat-send-btn"
        >
          <Send size={14} /> Ask
        </button>
      </form>

      {error && (
        <p style={{ color: "var(--danger)", fontFamily: "var(--font-mono)", fontSize: 12, marginTop: 10 }} data-testid="chat-error">
          {error}
        </p>
      )}
    </section>
  );
}
