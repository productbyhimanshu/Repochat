/**
 * AutoBrief.jsx — 4-section repository brief.
 *
 * Phase 1 stub: renders mock data from /index response.
 * Full design and styling implemented in Phase 5.
 *
 * Sections (from session_store.brief):
 *   1. architecture   — narrative summary
 *   2. core_modules   — top files with role + badge
 *   3. hidden_signals — insight cards (violations, churn, todos)
 *   4. unused_data    — stale fields
 */

export default function AutoBrief({ brief }) {
  if (!brief) return null;

  return (
    <div id="auto-brief" style={{ marginBottom: 40 }}>
      <h2 style={{ fontSize: 22, color: "#e6edf3", marginBottom: 24 }}>Repository Brief</h2>

      {/* Section 1 — Architecture */}
      <section id="brief-architecture" style={sectionStyle}>
        <h3 style={sectionTitle}>🏗 Architecture</h3>
        <p style={{ color: "#8b949e", lineHeight: 1.7 }}>{brief.architecture}</p>
      </section>

      {/* Section 2 — Core Modules */}
      <section id="brief-core-modules" style={sectionStyle}>
        <h3 style={sectionTitle}>📦 Core Modules</h3>
        {brief.core_modules?.map((mod, i) => (
          <div key={i} style={rowStyle}>
            <span style={{ color: "#79c0ff", fontFamily: "monospace" }}>{mod.file}</span>
            <span style={{ color: "#8b949e", marginLeft: 12 }}>{mod.role}</span>
            <span style={badgeStyle}>{mod.badge}</span>
          </div>
        ))}
      </section>

      {/* Section 3 — Hidden Signals */}
      <section id="brief-hidden-signals" style={sectionStyle}>
        <h3 style={sectionTitle}>🔍 Hidden Signals</h3>
        {brief.hidden_signals?.map((sig, i) => (
          <div key={i} style={cardStyle}>
            <strong style={{ color: "#f0883e" }}>{sig.title}</strong>
            <p style={{ margin: "6px 0 0", color: "#8b949e", fontSize: 14, lineHeight: 1.6 }}>{sig.detail}</p>
            <span style={{ fontSize: 12, color: "#484f58" }}>Source: {sig.source}</span>
          </div>
        ))}
      </section>

      {/* Section 4 — Unused Data */}
      <section id="brief-unused-data" style={sectionStyle}>
        <h3 style={sectionTitle}>🗑 Unused Data</h3>
        {brief.unused_data?.map((item, i) => (
          <div key={i} style={rowStyle}>
            <span style={{ color: "#d2a8ff", fontFamily: "monospace" }}>{item.field}</span>
            <span style={{ color: "#8b949e", marginLeft: 12 }}>{item.note}</span>
            <span style={badgeStyle}>{item.tag}</span>
          </div>
        ))}
      </section>
    </div>
  );
}

// ── inline styles (replaced with proper CSS in Phase 5) ──────────────────────

const sectionStyle = {
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 8,
  padding: "20px 24px",
  marginBottom: 16,
};

const sectionTitle = {
  fontSize: 15,
  fontWeight: 600,
  color: "#e6edf3",
  marginTop: 0,
  marginBottom: 16,
};

const rowStyle = {
  display: "flex",
  alignItems: "center",
  padding: "6px 0",
  borderBottom: "1px solid #21262d",
};

const cardStyle = {
  background: "#0d1117",
  border: "1px solid #30363d",
  borderRadius: 6,
  padding: "12px 16px",
  marginBottom: 10,
};

const badgeStyle = {
  marginLeft: "auto",
  fontSize: 12,
  color: "#7ee787",
  background: "#1a2f23",
  borderRadius: 4,
  padding: "2px 8px",
};
