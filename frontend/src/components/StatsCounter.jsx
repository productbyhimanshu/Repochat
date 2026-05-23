/**
 * StatsCounter.jsx — landing-page shareability chip ("X repos understood").
 * Fetches /api/stats on mount; silent on failure.
 */

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "../lib/api.js";

export default function StatsCounter() {
  const [count, setCount] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .stats()
      .then((data) => {
        if (!cancelled) setCount(Number(data?.repos_analyzed || 0));
      })
      .catch(() => {
        /* silent: counter is decorative */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (count === null || count === undefined) return null;

  return (
    <div
      className="stats-chip"
      data-testid="stats-counter"
      title={`${count.toLocaleString()} repositories understood so far`}
    >
      <Sparkles size={11} />
      <strong>{count.toLocaleString()}</strong>
      <span>repos understood</span>
    </div>
  );
}
