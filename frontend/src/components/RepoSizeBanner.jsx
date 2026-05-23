/**
 * RepoSizeBanner.jsx — warns the user if the indexed repo is over 200 files.
 * Phase 6 polish.
 */

import { AlertTriangle } from "lucide-react";

const LIMIT = 200;

export default function RepoSizeBanner({ totalFiles }) {
  if (!totalFiles || totalFiles <= LIMIT) return null;
  return (
    <div
      data-testid="repo-size-banner"
      style={{
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        padding: "14px 18px",
        marginBottom: 28,
        borderRadius: 12,
        border: "1px solid rgba(216,180,101,0.4)",
        background: "linear-gradient(180deg, #1c1810, #14110d)",
      }}
    >
      <AlertTriangle size={18} color="var(--gold)" style={{ marginTop: 2, flexShrink: 0 }} />
      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--gold)", marginBottom: 4 }}>
          Large repository
        </div>
        <div style={{ color: "var(--text-dim)", fontSize: 14, lineHeight: 1.55 }}>
          This repo has <strong style={{ color: "var(--text)" }}>{totalFiles.toLocaleString()} files</strong> — over RepoChat's
          {" "}<strong style={{ color: "var(--text)" }}>{LIMIT}-file</strong> sweet spot. The brief still works,
          but it focuses on the top-8 most central source files. Drift signals may be partial.
        </div>
      </div>
    </div>
  );
}
