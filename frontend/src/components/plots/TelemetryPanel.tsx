import { useMemo } from "react";
import { useChannel } from "../../hooks/useChannel";

interface Props {
  topic: string;
}

export default function TelemetryPanel({ topic }: Props) {
  const payload = useChannel<{ timestamp?: number; latency_ms?: number }>(topic);
  const rows = useMemo(() => Object.entries(payload || {}), [payload]);

  return (
    <section>
      <h2>Telemetry: {topic}</h2>
      {rows.length === 0 ? (
        <p>No data yet</p>
      ) : (
        <table>
          <tbody>
            {rows.map(([key, value]) => (
              <tr key={key}>
                <td>{key}</td>
                <td>{String(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
