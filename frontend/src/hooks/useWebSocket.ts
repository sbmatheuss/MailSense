import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/stores/uiStore";

type WSMessage = { type: string; [key: string]: unknown };

export function useWebSocket(onMessage: (msg: WSMessage) => void) {
  const token = useAuthStore((s) => s.token);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!token) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/notifications/`);

    ws.onmessage = (e) => {
      try {
        onMessageRef.current(JSON.parse(e.data));
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      // reconnect after 3s on unexpected close
      setTimeout(connect, 3000);
    };

    wsRef.current = ws;
  }, [token]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);
}
