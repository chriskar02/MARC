import { useEffect, useState } from "react";
import { useWebSocketContext } from "../providers/WebSocketProvider";

export function useChannel<TPayload = any>(topic: string) {
  const { subscribe } = useWebSocketContext();
  const [data, setData] = useState<TPayload | null>(null);

  useEffect(() => {
    const unsubscribe = subscribe(topic, (_, payload) => {
      setData(payload as TPayload);
    });
    return () => unsubscribe();
  }, [topic, subscribe]);

  return data;
}
