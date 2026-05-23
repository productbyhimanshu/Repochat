/**
 * UrlInput.jsx — Landing screen: paste a GitHub URL.
 *
 * Phase 5: hero layout with editorial typography, example chips,
 * and an inline preview of "what you'll see".
 */

import { useState } from "react";
import { ArrowRight, Github, AlertCircle } from "lucide-react";
import StatsCounter from "./StatsCounter.jsx";

const EXAMPLES = [
  "https://github.com/expressjs/express",
  "https://github.com/tiangolo/fastapi",
  "https://github.com/pallets/flask",
];

export default function UrlInput({ onSubmit, error }) {
  const [url, setUrl] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onSubmit(trimmed);
  }

  function pickExample(u) {
    setUrl(u);
  }

  return (
    <div className="landing" data-testid="landing-view">
      <div className="container">
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark">repo<em>chat</em></span>
            <span className="brand-tag">comprehension layer</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <StatsCounter />
            <a
              className="brand-tag"
              href="https://github.com/productbyhimanshu/Repochat"
              target="_blank"
              rel="noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, textDecoration: "none" }}
            >
              <Github size={13} /> on github
            </a>
          </div>
        </header>

        <div className="landing-body">
          <div>
            <div className="hero-eyebrow">
              <span className="dot" /> built it with ai · understand it with repochat
            </div>

            <h1 className="hero-headline" data-testid="hero-headline">
              You shipped a codebase.
              <br />
              Now <em>actually understand it.</em>
            </h1>

            <p className="hero-sub">
              Paste a public GitHub URL. Before you ask a single question, RepoChat
              reads the repo end-to-end and tells you how it's structured, what's
              drifting, and which files are quietly accumulating risk.
            </p>

            <form className="url-form" onSubmit={handleSubmit} data-testid="url-form">
              <input
                className="input"
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo"
                data-testid="repo-url-input"
                autoFocus
              />
              <button
                className="btn btn-primary"
                type="submit"
                disabled={!url.trim()}
                data-testid="analyze-btn"
              >
                Analyze <ArrowRight size={16} />
              </button>
            </form>

            {error && (
              <div className="url-error" data-testid="url-error">
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <div className="examples">
              <span className="examples-label">try</span>
              {EXAMPLES.map((u) => (
                <button
                  key={u}
                  className="example-chip"
                  onClick={() => pickExample(u)}
                  type="button"
                  data-testid={`example-${u.split("/").pop()}`}
                >
                  {u.replace("https://github.com/", "")}
                </button>
              ))}
            </div>
          </div>

          <div className="hero-preview" data-testid="hero-preview">
            <div className="eyebrow" style={{ marginBottom: 14 }}>
              what you'll get · in &lt; 30s
            </div>
            <div className="preview-row">
              <span className="dot-color" style={{ background: "var(--accent)" }} />
              Plain-English architecture summary
            </div>
            <div className="preview-row">
              <span className="dot-color" style={{ background: "var(--violet)" }} />
              Top 8 files by centrality
            </div>
            <div className="preview-row">
              <span className="dot-color" style={{ background: "var(--gold)" }} />
              Hidden signals · violations · churn
            </div>
            <div className="preview-row">
              <span className="dot-color" style={{ background: "var(--danger)" }} />
              Unused schema fields &amp; drift
            </div>
            <div className="preview-row" style={{ marginTop: 14, background: "var(--accent-soft)", color: "var(--accent)" }}>
              + conversational Q&amp;A with source citations
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
