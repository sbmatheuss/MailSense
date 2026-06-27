import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/stores/uiStore";

type WSMessage = { type: string; [key: string]: unknown };

const RECONNECT_DELAY_MS = 3_000;
const MAX_RECONNECT_ATTEMPTS = 8;

export function useWebSocket(onMessage: (msg: WSMessage) => void) {
  const token = useAuthStore((s) => s.token);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const attemptsRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!token || attemptsRef.current >= MAX_RECONNECT_ATTEMPTS) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/ws/notifications/?token=${token}`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      attemptsRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        onMessageRef.current(JSON.parse(e.data));
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (!token) return;
      attemptsRef.current += 1;
      timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };
  }, [token]);

  useEffect(() => {
    connect();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
