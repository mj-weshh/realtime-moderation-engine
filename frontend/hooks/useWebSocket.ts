"use client";

import { useEffect, useRef, useState } from "react";

export type ScoredComment = {
  event_id: string;
  user_id: string;
  text: string;
  timestamp: string;
  reply_to_id: string | null;
  scores: Record<string, number>;
  is_flagged: boolean;
};

export type ConnectionStatus = "connecting" | "open" | "closed" | "error";

const DEFAULT_WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8081";

type UseWebSocketOptions = {
  url?: string;
  onMessage?: (payload: ScoredComment) => void;
};

function isScoredComment(value: unknown): value is ScoredComment {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.event_id === "string" &&
    typeof record.scores === "object" &&
    record.scores !== null
  );
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const wsUrl = options.url ?? DEFAULT_WS_URL;
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const onMessageRef = useRef(options.onMessage);

  useEffect(() => {
    onMessageRef.current = options.onMessage;
  }, [options.onMessage]);

  useEffect(() => {
    let mounted = true;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (!mounted) return;
      setStatus("open");
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const parsed: unknown = JSON.parse(event.data as string);
        if (!isScoredComment(parsed)) return;
        onMessageRef.current?.(parsed);
      } catch {
        if (mounted) {
          setError("Failed to parse WebSocket message");
        }
      }
    };

    ws.onerror = () => {
      if (!mounted) return;
      setStatus("error");
      setError("WebSocket connection error");
    };

    ws.onclose = () => {
      if (!mounted) return;
      setStatus("closed");
    };

    return () => {
      mounted = false;
      ws.close(1000, "Component unmounted");
    };
  }, [wsUrl]);

  return { status, error };
}
