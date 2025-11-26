import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

type MessageHandler = (topic: string, payload: unknown) => void;

type WsContextValue = {
  subscribe: (topic: string, handler: MessageHandler) => () => void;
  send?: (payload: Record<string, unknown>) => void;
};

const WebSocketContext = createContext<WsContextValue | null>(null);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const handlers = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const sockets = useRef<Map<string, WebSocket>>(new Map());
  const wsConnectRequests = useRef<Set<string>>(new Set());
  const baseUrl = useMemo(() => {
    return (import.meta as any).env.VITE_BACKEND_WS_URL || "ws://127.0.0.1:8000";
  }, []);

  // Helper to determine which websocket a topic needs
  const getWsPath = (topic: string): string => {
    if (topic.startsWith("worker/") && topic.includes("/frame")) {
      // Extract worker name from topic like "worker/basler_camera/frame"
      const parts = topic.split("/");
      if (parts.length >= 2) {
        return `/ws/camera/${parts[1]}`;
      }
    }
    return "/ws/telemetry";
  };

  // Effect to maintain websocket connections
  useEffect(() => {
    // For each requested path, ensure we have a connection
    const pathsToConnect = Array.from(wsConnectRequests.current);
    
    for (const wsPath of pathsToConnect) {
      if (sockets.current.has(wsPath)) {
        continue; // Already connected
      }

      let isMounted = true;
      let ws: WebSocket;

      const connect = () => {
        if (!isMounted) return;
        console.log(`[WS] Connecting to ${wsPath}`);
        ws = new WebSocket(`${baseUrl}${wsPath}`);
        
        ws.onopen = () => {
          if (!isMounted) return;
          console.log(`[WS] Connected to ${wsPath}`);
          sockets.current.set(wsPath, ws);
        };
        
        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const parsed = JSON.parse(event.data);
            const topic = parsed.topic as string;
            const payload = parsed.payload;
            console.log(`[WS] Received on ${topic}:`, { payloadKeys: Object.keys(payload || {}) });
            const topicHandlers = handlers.current.get(topic);
            if (topicHandlers && topicHandlers.size > 0) {
              topicHandlers.forEach((cb) => cb(topic, payload));
            } else {
              console.warn(`[WS] No handlers registered for topic: ${topic}`);
            }
          } catch (err) {
            console.error("WS parse error", err);
          }
        };
        
        ws.onclose = () => {
          if (!isMounted) return;
          console.log(`[WS] Disconnected from ${wsPath}`);
          sockets.current.delete(wsPath);
          // Retry after delay
          setTimeout(connect, 1000);
        };
        
        ws.onerror = (err) => {
          console.error(`[WS] Error on ${wsPath}:`, err);
        };
      };

      connect();

      // Cleanup function
      return () => {
        isMounted = false;
        ws?.close();
      };
    }
  }, [baseUrl]);

  const value = useMemo<WsContextValue>(() => {
    return {
      subscribe(topic, handler) {
        console.log(`[WS] Subscribe to topic: ${topic}`);
        // Determine which websocket this topic needs
        const wsPath = getWsPath(topic);
        console.log(`[WS] Topic ${topic} maps to WS path: ${wsPath}`);
        
        // Request this websocket connection
        wsConnectRequests.current.add(wsPath);

        if (!handlers.current.has(topic)) {
          handlers.current.set(topic, new Set());
        }
        const bucket = handlers.current.get(topic)!;
        bucket.add(handler);
        console.log(`[WS] Handler registered for ${topic}, total handlers: ${bucket.size}`);
        
        return () => {
          bucket.delete(handler);
          // If no more handlers for this topic, we could clean up the websocket
          // But for simplicity, we'll keep it connected
        };
      },
      send(payload) {
        const ws = sockets.current.get("/ws/telemetry");
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(payload));
        }
      },
    };
  }, []);

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocketContext() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("WebSocketContext missing. Wrap components with WebSocketProvider.");
  }
  return ctx;
}
