import { useChannel } from "../../hooks/useChannel";

interface BotaData {
  fx: number;
  fy: number;
  fz: number;
  tx: number;
  ty: number;
  tz: number;
  timestamp?: number;
}

export default function BotaFeedback() {
  const botaData = useChannel<BotaData>("worker/bota_sensor/ft_sample");

  if (!botaData) {
    return (
      <section className="panel">
        <h2>Bota MiniONE Pro F/T Sensor</h2>
        <div style={{ padding: "2rem", textAlign: "center", color: "#8b949e" }}>
          Waiting for sensor data...
        </div>
      </section>
    );
  }

  const forceNorm = Math.sqrt(botaData.fx ** 2 + botaData.fy ** 2 + botaData.fz ** 2);
  const torqueNorm = Math.sqrt(botaData.tx ** 2 + botaData.ty ** 2 + botaData.tz ** 2);

  return (
    <section className="panel">
      <h2>Bota MiniONE Pro F/T Sensor</h2>

      <div className="feedback-grid">
        <div className="feedback-item">
          <div className="feedback-label">Force Magnitude</div>
          <div className="feedback-value">{forceNorm.toFixed(2)} N</div>
        </div>
        <div className="feedback-item">
          <div className="feedback-label">Torque Magnitude</div>
          <div className="feedback-value">{torqueNorm.toFixed(2)} N·m</div>
        </div>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <div className="feedback-label" style={{ marginBottom: "0.5rem" }}>
          Force Vector (N)
        </div>
        <div className="vector-display">
          <div className="vector-component">
            <span className="vector-label">Fx</span>
            <span className="vector-value">{botaData.fx.toFixed(3)}</span>
          </div>
          <div className="vector-component">
            <span className="vector-label">Fy</span>
            <span className="vector-value">{botaData.fy.toFixed(3)}</span>
          </div>
          <div className="vector-component">
            <span className="vector-label">Fz</span>
            <span className="vector-value">{botaData.fz.toFixed(3)}</span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <div className="feedback-label" style={{ marginBottom: "0.5rem" }}>
          Torque Vector (N·m)
        </div>
        <div className="vector-display">
          <div className="vector-component">
            <span className="vector-label">Tx</span>
            <span className="vector-value">{botaData.tx.toFixed(3)}</span>
          </div>
          <div className="vector-component">
            <span className="vector-label">Ty</span>
            <span className="vector-value">{botaData.ty.toFixed(3)}</span>
          </div>
          <div className="vector-component">
            <span className="vector-label">Tz</span>
            <span className="vector-value">{botaData.tz.toFixed(3)}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
