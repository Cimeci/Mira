"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface SSEEvent<T = unknown> {
  kind: string;
  event?: T;
  case_id?: string;
  url?: string;
  text?: string;
  statuses?: Record<string, string>;
  message?: string;
}

interface UseEventSourceOptions<T> {
  url: string;
  onMessage?: (event: SSEEvent<T>) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  enabled?: boolean;
  withCredentials?: boolean;
}

const MAX_RECONNECT_DELAY_MS = 30000;

export function useEventSource<T = unknown>({
  url,
  onMessage,
  onError,
  onOpen,
  enabled = true,
  withCredentials = false,
}: UseEventSourceOptions<T>) {
  const [readyState, setReadyState] = useState<number>(0);
  const [lastEvent, setLastEvent] = useState<SSEEvent<T> | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  // Set when we close on purpose (disconnect / disabled) so a trailing onerror
  // from the closing socket does not schedule a reconnect.
  const manualClose = useRef(false);

  // Callbacks live in refs so `connect` never changes identity just because the
  // parent re-rendered with a fresh inline handler. Without this, every received
  // event re-renders the consumer, rebuilds `connect`, and the effect tears down
  // and reopens the stream — which replays the whole backlog and loops forever.
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);
  const onOpenRef = useRef(onOpen);
  onMessageRef.current = onMessage;
  onErrorRef.current = onError;
  onOpenRef.current = onOpen;

  const disconnect = useCallback(() => {
    manualClose.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setReadyState(SSE_READY_STATES.CLOSED);
  }, []);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;
    manualClose.current = false;

    const es = new EventSource(url, { withCredentials });
    eventSourceRef.current = es;

    es.onopen = () => {
      setReadyState(es.readyState);
      reconnectAttempts.current = 0;
      onOpenRef.current?.();
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent<T>;
        setLastEvent(data);
        onMessageRef.current?.(data);
      } catch {
        // Ignore non-JSON keep-alive frames.
      }
    };

    es.onerror = (error) => {
      setReadyState(es.readyState);
      onErrorRef.current?.(error);

      // Reconnect with exponential backoff — unless we closed on purpose.
      if (es.readyState === EventSource.CLOSED && !manualClose.current) {
        es.close();
        const delay = Math.min(
          1000 * 2 ** reconnectAttempts.current,
          MAX_RECONNECT_DELAY_MS
        );
        reconnectAttempts.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };
  }, [url, enabled, withCredentials]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { readyState, lastEvent, connect, disconnect };
}

export const SSE_READY_STATES = {
  CONNECTING: 0,
  OPEN: 1,
  CLOSED: 2,
} as const;
