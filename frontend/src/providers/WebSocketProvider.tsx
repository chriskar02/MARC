import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

type MessageHandler = (topic: string, payload: unknown) => void;

type WsContextValue = {
  subscribe: (topic: string, handler: MessageHandler) => () => void;
  send?: (payload: Record<string, unknown>) => void;
};

const WebSocketContext = createContext<WsContextValue | null>(null);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const handlers = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const wsUrl = useMemo(() => {
    const base = import.meta.env.VITE_BACKEND_WS_URL || "ws://127.0.0.1:8000";
    return `${base}/ws/telemetry`;
  }, []);

  useEffect(() => {
    let isMounted = true;
    let ws: WebSocket;

    const connect = () => {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setSocket(ws);
      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          const topic = parsed.topic as string;
          const payload = parsed.payload;
          const topicHandlers = handlers.current.get(topic);
          topicHandlers?.forEach((cb) => cb(topic, payload));
        } catch (err) {
          console.error("WS parse error", err);
        }
      };
      ws.onclose = () => {
        setSocket(null);
        if (isMounted) {
          setTimeout(connect, 1000);
        }
      };
    };

    connect();
    return () => {
      isMounted = false;
      ws?.close();
    };
  }, [wsUrl]);

  const value = useMemo<WsContextValue>(() => {
    return {
      subscribe(topic, handler) {
        if (!handlers.current.has(topic)) {
          handlers.current.set(topic, new Set());
        }
        const bucket = handlers.current.get(topic)!;
        bucket.add(handler);
        return () => bucket.delete(handler);
      },
      send(payload) {
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify(payload));
        }
      },
    };
  }, [socket]);

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocketContext() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("WebSocketContext missing. Wrap components with WebSocketProvider.");
  }
  return ctx;
}
