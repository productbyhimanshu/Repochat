/**
 * Loading.jsx — Indeterminate progress UI for the indexing phase.
 *
 * Simulates the parallel agent dispatch: Index Agent, Signal Agent, Brief.
 * Steps advance on timed thresholds — visual feedback only;
 * the backend completes whenever it's done.
 */

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Sparkles } from "lucide-react";

const STEPS = [
  { id: "tree",     label: "Reading file tree from GitHub" },
  { id: "centrality", label: "Building dependency graph · scoring centrality" },
  { id: "signals", label: "Scanning for TODOs, churn & architectural drift" },
  { id: "brief",   label: "Composing your auto-brief with Claude Sonnet 4.5" },
];

export default function Loading() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const intervals = [2500, 6000, 11000];
    const timers = intervals.map((delay, i) =>
      setTimeout(() => setActive(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="loading-screen" data-testid="loading-view">
      <div style={{ textAlign: "center" }}>
        <div className="eyebrow" style={{ marginBottom: 14 }}>
          parallel agents · in flight
        </div>
        <h2 className="loading-title">
          Reading your <em>codebase</em>…
        </h2>
      </div>

      <div className="loading-steps">
        {STEPS.map((step, i) => {
          const isDone = i < active;
          const isActive = i === active;
          return (
            <div
              key={step.id}
              className={`loading-step ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
              data-testid={`loading-step-${step.id}`}
            >
              <span className="step-icon">
                {isDone ? (
                  <CheckCircle2 size={14} />
                ) : isActive ? (
                  <Loader2 size={14} className="spin" style={{ animation: "spin 1s linear infinite" }} />
                ) : (
                  <Sparkles size={12} opacity={0.4} />
                )}
              </span>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      <div className="loading-progress" />

      <p style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--muted)", letterSpacing: "0.08em", margin: 0 }}>
        large repos may take 20-40 seconds
      </p>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
