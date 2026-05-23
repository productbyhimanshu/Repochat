/**
 * ErrorBoundary.jsx — catches unhandled render errors so the user
 * never sees a blank screen. Phase 6 polish.
 */

import React from "react";
import { AlertCircle, RefreshCcw } from "lucide-react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("RepoChat render error:", error, info);
  }

  handleReset = () => {
    this.setState({ error: null });
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 20px",
          gap: 20,
        }}
        data-testid="error-boundary"
      >
        <AlertCircle size={36} color="var(--danger)" />
        <h2 className="loading-title" style={{ margin: 0 }}>
          Something <em>came loose</em>.
        </h2>
        <p style={{ color: "var(--text-dim)", maxWidth: 460, textAlign: "center", margin: 0 }}>
          The UI hit an error it could not recover from. Reload to start over —
          your repo URL is safe.
        </p>
        <pre
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--muted)",
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: "12px 16px",
            maxWidth: 520,
            overflowX: "auto",
          }}
        >
          {String(this.state.error?.message || this.state.error)}
        </pre>
        <button
          className="btn btn-primary"
          onClick={this.handleReset}
          data-testid="error-reload-btn"
        >
          <RefreshCcw size={14} /> Reload
        </button>
      </div>
    );
  }
}
