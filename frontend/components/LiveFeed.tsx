"use client";

import { useCallback, useState } from "react";
import {
  ScoredComment,
  useWebSocket,
} from "@/hooks/useWebSocket";

const MAX_ALERTS = 100;

function getToxicityStyles(toxicity: number): string {
  if (toxicity >= 0.8) {
    return "border-red-500/60 bg-red-950/30 text-red-400";
  }
  return "border-amber-500/60 bg-amber-950/20 text-amber-300";
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleTimeString();
}

export default function LiveFeed() {
  const [alerts, setAlerts] = useState<ScoredComment[]>([]);

  const handleMessage = useCallback((payload: ScoredComment) => {
    setAlerts((prev) => [payload, ...prev].slice(0, MAX_ALERTS));
  }, []);

  const { status, error } = useWebSocket({ onMessage: handleMessage });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {status === "connecting" && (
        <div className="border-b border-command-border bg-command-surface px-4 py-2 text-xs text-command-muted">
          Connecting to alert stream...
        </div>
      )}
      {status === "error" && (
        <div className="border-b border-red-500/40 bg-red-950/30 px-4 py-2 text-xs text-red-400">
          {error ?? "WebSocket connection error"}
        </div>
      )}
      {status === "closed" && (
        <div className="border-b border-command-border bg-command-surface px-4 py-2 text-xs text-command-muted">
          Disconnected from alert stream
        </div>
      )}

      <ul className="min-h-0 flex-1 overflow-y-auto p-3 space-y-2">
        {alerts.length === 0 && status === "open" && (
          <li className="px-2 py-8 text-center text-sm text-command-muted">
            Waiting for flagged comments...
          </li>
        )}
        {alerts.map((alert) => {
          const toxicity = alert.scores.toxicity ?? 0;
          return (
            <li
              key={alert.event_id}
              className={`rounded-md border px-3 py-2 ${getToxicityStyles(toxicity)}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold">{alert.user_id}</span>
                <span className="shrink-0 rounded bg-black/30 px-1.5 py-0.5 text-xs font-mono">
                  {(toxicity * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-1 line-clamp-3 text-sm leading-snug">
                {alert.text}
              </p>
              <p className="mt-1 text-xs opacity-70">
                {formatTimestamp(alert.timestamp)}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
