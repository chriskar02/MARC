import { createContext, useContext, useCallback, useEffect, useMemo, useRef } from "react";

type MessageHandler = (topic: string, payload: unknown) => void;

type WsContextValue = {
  subscribe: (topic: string, handler: MessageHandler) => () => void;
  send?: (payload: Record<string, unknown>) => void;
};

const WebSocketContext = createContext<WsContextValue | null>(null);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const handlers = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const sockets = useRef<Map<string, WebSocket>>(new Map());
  const reconnectTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const mountedRef = useRef(true);

  const baseUrl = useMemo(() => {
    return (import.meta as any).env.VITE_BACKEND_WS_URL || "ws://127.0.0.1:8000";
  }, []);

  // Determine which websocket path a topic needs
  const getWsPath = useCallback((topic: string): string => {
    if (topic.startsWith("worker/") && topic.includes("/frame")) {
      const parts = topic.split("/");
      if (parts.length >= 2) return `/ws/camera/${parts[1]}`;
    }
    if (topic.startsWith("worker/") && topic.includes("/ft_sample")) {
      const parts = topic.split("/");
      if (parts.length >= 2) return `/ws/sensor/${parts[1]}`;
    }
    return "/ws/telemetry";
  }, []);

  // Open a websocket for a given path (idempotent)
  const ensureConnection = useCallback((wsPath: string) => {
    if (sockets.current.has(wsPath)) return; // already open / opening
    // Mark as pending so we don't double-connect
    const sentinel = {} as unknown as WebSocket;
    sockets.current.set(wsPath, sentinel);

    const connect = () => {
      if (!mountedRef.current) return;
      console.log(`[WS] Connecting to ${wsPath}`);
      const ws = new WebSocket(`${baseUrl}${wsPath}`);

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        console.log(`[WS] Connected to ${wsPath}`);
        sockets.current.set(wsPath, ws);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data);
          const topic = parsed.topic as string;
          const payload = parsed.payload;
          const topicHandlers = handlers.current.get(topic);
          if (topicHandlers && topicHandlers.size > 0) {
            topicHandlers.forEach((cb) => cb(topic, payload));
          }
        } catch (err) {
          console.error("WS parse error", err);
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        console.log(`[WS] Disconnected from ${wsPath}`);
        sockets.current.delete(wsPath);
        // Retry
        const timer = setTimeout(() => {
          reconnectTimers.current.delete(wsPath);
          ensureConnection(wsPath);
        }, 1500);
        reconnectTimers.current.set(wsPath, timer);
      };

      ws.onerror = (err) => {
        console.error(`[WS] Error on ${wsPath}`, err);
      };

      sockets.current.set(wsPath, ws);
    };

    connect();
  }, [baseUrl]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      sockets.current.forEach((ws) => { try { ws.close(); } catch {} });
      sockets.current.clear();
      reconnectTimers.current.forEach((t) => clearTimeout(t));
      reconnectTimers.current.clear();
    };
  }, []);

  const value = useMemo<WsContextValue>(() => {
    return {
      subscribe(topic, handler) {
        // Ensure WS connection for this topic
        const wsPath = getWsPath(topic);
        ensureConnection(wsPath);

        if (!handlers.current.has(topic)) {
          handlers.current.set(topic, new Set());
        }
        const bucket = handlers.current.get(topic)!;
        bucket.add(handler);

        return () => {
          bucket.delete(handler);
        };
      },
      send(payload) {
        const ws = sockets.current.get("/ws/telemetry");
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(payload));
        }
      },
    };
  }, [getWsPath, ensureConnection]);

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocketContext() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("WebSocketContext missing. Wrap components with WebSocketProvider.");
  }
  return ctx;
}
