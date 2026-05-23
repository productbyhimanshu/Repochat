/**
 * UrlInput.jsx — GitHub repo URL input.
 *
 * Phase 1 stub: validates URL format on client side,
 * calls onSubmit(url) which hits POST /index.
 * Full styling in Phase 5.
 */

import { useState } from "react";

export default function UrlInput({ onSubmit, error }) {
  const [url, setUrl] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onSubmit(trimmed);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh", padding: "20px" }}>
      <h1 style={{ fontSize: 32, marginBottom: 8, color: "#e6edf3" }}>Repochat</h1>
      <p style={{ color: "#8b949e", marginBottom: 32 }}>
        Paste a public GitHub repo URL to get an instant AI brief
      </p>
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 12, width: "100%", maxWidth: 600 }}>
        <input
          id="repo-url-input"
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          style={{
            flex: 1,
            padding: "12px 16px",
            borderRadius: 8,
            border: "1px solid #30363d",
            background: "#161b22",
            color: "#e6edf3",
            fontSize: 15,
            outline: "none",
          }}
        />
        <button
          id="analyze-btn"
          type="submit"
          style={{
            padding: "12px 24px",
            borderRadius: 8,
            border: "none",
            background: "#238636",
            color: "#fff",
            fontSize: 15,
            cursor: "pointer",
          }}
        >
          Analyze
        </button>
      </form>
      {error && (
        <p id="url-error" style={{ color: "#f85149", marginTop: 16, fontSize: 14 }}>
          {error}
        </p>
      )}
    </div>
  );
}
