/**
 * api.js — Shared API helper for RepoChat.
 * Uses REACT_APP_BACKEND_URL (provided by Vite via define) and /api prefix.
 */

const BASE = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");

async function postJSON(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Server error ${res.status}`;
    try {
      const data = await res.json();
      if (Array.isArray(data?.detail)) {
        detail = data.detail.map((e) => e?.msg || JSON.stringify(e)).join("; ");
      } else if (typeof data?.detail === "string") {
        detail = data.detail;
      } else if (data?.detail) {
        detail = JSON.stringify(data.detail);
      }
    } catch {
      /* ignore */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const err = new Error(`Server error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  index:  (url) => postJSON("/api/index", { url }),
  chat:   (session_id, question) => postJSON("/api/chat", { session_id, question }),
  stats:  () => getJSON("/api/stats"),
  health: () => getJSON("/api/health"),
};

export function fileUrl(repoMeta, path) {
  if (!repoMeta || !path) return null;
  const branch = repoMeta.default_branch || "HEAD";
  return `https://github.com/${repoMeta.owner}/${repoMeta.repo}/blob/${branch}/${path}`;
}
