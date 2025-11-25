import { useMemo } from "react";
import { useChannel } from "../../hooks/useChannel";

interface Props {
  workerName: string;
}

export default function CameraStream({ workerName }: Props) {
  const frame = useChannel<{ data: string; metadata?: Record<string, unknown> }>(
    `worker/${workerName}/frame`
  );

  const blobUrl = useMemo(() => {
    if (!frame?.data) return null;
    const buffer = Uint8Array.from(atob(frame.data), (c) => c.charCodeAt(0));
    const blob = new Blob([buffer], { type: "application/octet-stream" });
    return URL.createObjectURL(blob);
  }, [frame]);

  return (
    <section>
      <h2>Camera: {workerName}</h2>
      {blobUrl ? (
        <img src={blobUrl} alt="camera" style={{ width: "100%", borderRadius: 8 }} />
      ) : (
        <div style={{ padding: "2rem", textAlign: "center", border: "1px dashed #555" }}>
          Waiting for frames...
        </div>
      )}
    </section>
  );
}
