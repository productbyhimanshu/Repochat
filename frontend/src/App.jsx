/**
 * App.jsx — Root state machine for RepoChat.
 *
 * States: idle → loading → brief_ready
 * Render order (locked): UrlInput → Loading → AutoBrief → Chat
 */

import { useCallback, useState } from "react";
import UrlInput from "./components/UrlInput.jsx";
import Loading from "./components/Loading.jsx";
import AutoBrief from "./components/AutoBrief.jsx";
import Chat from "./components/Chat.jsx";
import { api } from "./lib/api.js";

export default function App() {
  const [appState, setAppState] = useState("idle"); // idle | loading | brief_ready
  const [sessionId, setSessionId] = useState(null);
  const [brief, setBrief] = useState(null);
  const [repoMeta, setRepoMeta] = useState(null);
  const [error, setError] = useState(null);

  const handleUrlSubmit = useCallback(async (url) => {
    setError(null);
    setAppState("loading");
    try {
      const data = await api.index(url);
      setSessionId(data.session_id);
      setBrief(data.brief);
      setRepoMeta(data.repo_meta);
      setAppState("brief_ready");
    } catch (err) {
      setError(err.message || "Something went wrong");
      setAppState("idle");
    }
  }, []);

  const handleReset = useCallback(() => {
    setAppState("idle");
    setSessionId(null);
    setBrief(null);
    setRepoMeta(null);
    setError(null);
  }, []);

  if (appState === "idle") {
    return <UrlInput onSubmit={handleUrlSubmit} error={error} />;
  }

  if (appState === "loading") {
    return <Loading />;
  }

  return (
    <div className="container brief-wrap" data-testid="brief-ready-view">
      <header className="app-header" style={{ paddingTop: 0, marginBottom: 12 }}>
        <div className="brand">
          <span className="brand-mark">repo<em>chat</em></span>
          <span className="brand-tag">comprehension layer</span>
        </div>
        <button
          className="reset-link"
          onClick={handleReset}
          data-testid="new-repo-btn"
        >
          ← analyze another repo
        </button>
      </header>

      <AutoBrief brief={brief} repoMeta={repoMeta} />
      <Chat sessionId={sessionId} repoMeta={repoMeta} />

      <div className="foot">
        repochat · built for the ai coding era · models: claude sonnet 4.5
      </div>
    </div>
  );
}
