/**
 * AutoBrief.jsx — 4-section repository brief.
 *
 * Sections (from session_store.brief):
 *   1. architecture   — narrative summary (editorial)
 *   2. core_modules   — top files with role + badge
 *   3. hidden_signals — insight cards; violation gets a "wow banner"
 *   4. unused_data    — stale fields
 *
 * THIS IS THE PRIMARY VIEW. It always renders above Chat.
 */

import { useMemo } from "react";
import { Layers, Boxes, Search, Trash2, AlertTriangle, GitCommit, ClipboardList, ExternalLink } from "lucide-react";
import { fileUrl } from "../lib/api.js";
import RepoSizeBanner from "./RepoSizeBanner.jsx";

function badgeClassFor(badge) {
  if (!badge) return "badge";
  const slug = String(badge).toLowerCase().replace(/[^a-z]/g, "");
  return `badge badge-${slug}`;
}

function signalIcon(type) {
  if (type === "violation") return <AlertTriangle size={11} />;
  if (type === "churn")     return <GitCommit size={11} />;
  if (type === "todo")      return <ClipboardList size={11} />;
  return <Search size={11} />;
}

export default function AutoBrief({ brief, repoMeta }) {
  if (!brief) return null;

  const violationSignal = useMemo(
    () => (brief.hidden_signals || []).find((s) => s.type === "violation"),
    [brief]
  );
  const otherSignals = useMemo(
    () => (brief.hidden_signals || []).filter((s) => s !== violationSignal),
    [brief, violationSignal]
  );

  return (
    <div data-testid="auto-brief">
      {/* Repo meta header */}
      <div className="brief-meta">
        <div>
          <h1 className="brief-repo-name" data-testid="brief-repo-name">
            <span className="owner">{repoMeta?.owner}/</span>{repoMeta?.repo}
          </h1>
          {repoMeta?.url && (
            <a
              className="brief-repo-url"
              href={repoMeta.url}
              target="_blank"
              rel="noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 6, textDecoration: "none" }}
            >
              {repoMeta.url} <ExternalLink size={11} />
            </a>
          )}
        </div>
        <div className="eyebrow" style={{ textAlign: "right" }}>
          auto-brief<br />
          <span style={{ color: "var(--accent)" }}>generated · {new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Optional warning for very large repos */}
      <RepoSizeBanner totalFiles={repoMeta?.total_files} />

      {/* Section 1 — Architecture */}
      <section className="section" data-testid="brief-architecture" style={{ animationDelay: "0ms" }}>
        <h2 className="section-title">
          <span className="num">01</span>
          <Layers size={18} style={{ color: "var(--accent)" }} />
          <span>The <em>architecture</em>, in one breath</span>
        </h2>
        <div className="card">
          <p className="arch-text" data-testid="brief-architecture-text">{brief.architecture}</p>
        </div>
      </section>

      {/* Section 2 — Core Modules */}
      <section className="section" data-testid="brief-core-modules" style={{ animationDelay: "80ms" }}>
        <h2 className="section-title">
          <span className="num">02</span>
          <Boxes size={18} style={{ color: "var(--violet)" }} />
          <span>The files that <em>actually matter</em></span>
        </h2>

        <div className="modules-grid">
          {(brief.core_modules || []).map((mod, i) => (
            <a
              key={`${mod.file}-${i}`}
              className="module-row"
              href={fileUrl(repoMeta, mod.file)}
              target="_blank"
              rel="noreferrer"
              style={{ textDecoration: "none", color: "inherit" }}
              data-testid={`module-row-${i}`}
            >
              <span className="module-rank">{String(i + 1).padStart(2, "0")}</span>
              <div className="module-main">
                <span className="module-file">{mod.file}</span>
                <span className="module-role">{mod.role}</span>
              </div>
              <span className={badgeClassFor(mod.badge)}>{mod.badge || "Module"}</span>
            </a>
          ))}
          {(!brief.core_modules || brief.core_modules.length === 0) && (
            <div className="empty">no source modules detected</div>
          )}
        </div>
      </section>

      {/* Section 3 — Hidden Signals (violation = wow banner) */}
      <section className="section" data-testid="brief-hidden-signals" style={{ animationDelay: "160ms" }}>
        <h2 className="section-title">
          <span className="num">03</span>
          <Search size={18} style={{ color: "var(--gold)" }} />
          <span>Hidden <em>signals</em> nobody told you about</span>
        </h2>

        {violationSignal && (
          <div className="wow-banner" data-testid="wow-violation">
            <span className="wow-tag">
              <AlertTriangle size={11} /> Architectural outlier
            </span>
            <p className="wow-text">{violationSignal.detail || violationSignal.title}</p>
            {violationSignal.source && (
              <div className="wow-source">source · {violationSignal.source}</div>
            )}
          </div>
        )}

        <div className="signals-grid">
          {otherSignals.map((sig, i) => (
            <div
              key={`${sig.title}-${i}`}
              className={`signal-card type-${sig.type || "info"}`}
              data-testid={`signal-card-${i}`}
            >
              <span className="signal-type">
                {signalIcon(sig.type)} {sig.type || "signal"}
              </span>
              <h3 className="signal-title">{sig.title}</h3>
              <p className="signal-detail">{sig.detail}</p>
              {sig.source && <span className="signal-source">· {sig.source}</span>}
            </div>
          ))}
          {otherSignals.length === 0 && !violationSignal && (
            <div className="empty">no hidden signals detected — this codebase is unusually clean.</div>
          )}
        </div>
      </section>

      {/* Section 4 — Unused Data */}
      <section className="section" data-testid="brief-unused-data" style={{ animationDelay: "240ms" }}>
        <h2 className="section-title">
          <span className="num">04</span>
          <Trash2 size={18} style={{ color: "var(--danger)" }} />
          <span>Data defined but <em>never used</em></span>
        </h2>

        <div className="unused-list">
          {(brief.unused_data || []).map((item, i) => (
            <div className="unused-row" key={`${item.field}-${i}`} data-testid={`unused-row-${i}`}>
              <span className="unused-field">{item.field}</span>
              <span className="unused-note">{item.note}</span>
              <span className={badgeClassFor(item.tag)}>{item.tag || "Stale"}</span>
            </div>
          ))}
          {(!brief.unused_data || brief.unused_data.length === 0) && (
            <div className="empty">no orphaned fields found.</div>
          )}
        </div>
      </section>
    </div>
  );
}
