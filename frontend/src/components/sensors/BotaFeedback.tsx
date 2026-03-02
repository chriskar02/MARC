import { useRef, useEffect, useCallback } from "react";
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

/* ── Rolling line chart (canvas-based, zero dependencies) ── */
const HISTORY_LEN = 200; // number of data points visible

function FyChart({ fy }: { fy: number | undefined }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bufRef = useRef<number[]>([]);

  // Push new value into the ring buffer
  useEffect(() => {
    if (fy === undefined) return;
    const buf = bufRef.current;
    buf.push(fy);
    if (buf.length > HISTORY_LEN) buf.shift();
  }, [fy]);

  // Repaint at ~20 fps via requestAnimationFrame
  const rafRef = useRef<number>(0);

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const buf = bufRef.current;

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = "rgba(13,17,23,0.8)";
    ctx.fillRect(0, 0, W, H);

    if (buf.length < 2) {
      ctx.fillStyle = "#8b949e";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Waiting for data…", W / 2, H / 2);
      rafRef.current = requestAnimationFrame(paint);
      return;
    }

    // Auto-scale Y range
    let lo = Infinity, hi = -Infinity;
    for (const v of buf) { if (v < lo) lo = v; if (v > hi) hi = v; }
    const margin = Math.max((hi - lo) * 0.15, 0.05);
    lo -= margin;
    hi += margin;

    // Zero line
    const zeroY = H - ((0 - lo) / (hi - lo)) * H;
    ctx.strokeStyle = "rgba(88,166,255,0.25)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(W, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Data line
    ctx.strokeStyle = "#3fb950";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    const stepX = W / (HISTORY_LEN - 1);
    const offset = HISTORY_LEN - buf.length;
    for (let i = 0; i < buf.length; i++) {
      const x = (offset + i) * stepX;
      const y = H - ((buf[i] - lo) / (hi - lo)) * H;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Y-axis labels
    ctx.fillStyle = "#8b949e";
    ctx.font = "10px monospace";
    ctx.textAlign = "left";
    ctx.fillText(`${hi.toFixed(2)} N`, 3, 12);
    ctx.fillText(`${lo.toFixed(2)} N`, 3, H - 4);

    // Latest value
    const last = buf[buf.length - 1];
    ctx.fillStyle = "#3fb950";
    ctx.font = "bold 11px monospace";
    ctx.textAlign = "right";
    ctx.fillText(`Fy = ${last.toFixed(3)} N`, W - 4, 12);

    rafRef.current = requestAnimationFrame(paint);
  }, []);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(paint);
    return () => cancelAnimationFrame(rafRef.current);
  }, [paint]);

  return (
    <canvas
      ref={canvasRef}
      width={320}
      height={100}
      style={{ width: "100%", height: "100px", borderRadius: 4, border: "1px solid #30363d" }}
    />
  );
}

export default function BotaFeedback() {
  const botaData = useChannel<BotaData>("worker/bota_sensor/ft_sample");

  if (!botaData) {
    return (
      <section className="panel">
        <h2>Bota MiniONE Pro F/T Sensor</h2>
        <div style={{ padding: "1rem", textAlign: "center", color: "#8b949e" }}>
          Waiting for sensor data…
        </div>
      </section>
    );
  }

  const forceNorm = Math.sqrt(botaData.fx ** 2 + botaData.fy ** 2 + botaData.fz ** 2);
  const torqueNorm = Math.sqrt(botaData.tx ** 2 + botaData.ty ** 2 + botaData.tz ** 2);

  return (
    <section className="panel">
      <h2>Bota MiniONE Pro F/T Sensor</h2>

      {/* ── Fy running graph ── */}
      <div style={{ marginBottom: "0.5rem" }}>
        <div className="feedback-label" style={{ marginBottom: "0.25rem" }}>Force Y (running)</div>
        <FyChart fy={botaData.fy} />
      </div>

      <div className="feedback-grid">
        <div className="feedback-item">
          <div className="feedback-label">Force |F|</div>
          <div className="feedback-value">{forceNorm.toFixed(2)} N</div>
        </div>
        <div className="feedback-item">
          <div className="feedback-label">Torque |T|</div>
          <div className="feedback-value">{torqueNorm.toFixed(2)} N·m</div>
        </div>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        <div className="feedback-label" style={{ marginBottom: "0.25rem" }}>Force (N)</div>
        <div className="vector-display">
          <div className="vector-component"><span className="vector-label">Fx</span><span className="vector-value">{botaData.fx.toFixed(3)}</span></div>
          <div className="vector-component"><span className="vector-label">Fy</span><span className="vector-value">{botaData.fy.toFixed(3)}</span></div>
          <div className="vector-component"><span className="vector-label">Fz</span><span className="vector-value">{botaData.fz.toFixed(3)}</span></div>
        </div>
      </div>

      <div style={{ marginTop: "0.5rem" }}>
        <div className="feedback-label" style={{ marginBottom: "0.25rem" }}>Torque (N·m)</div>
        <div className="vector-display">
          <div className="vector-component"><span className="vector-label">Tx</span><span className="vector-value">{botaData.tx.toFixed(3)}</span></div>
          <div className="vector-component"><span className="vector-label">Ty</span><span className="vector-value">{botaData.ty.toFixed(3)}</span></div>
          <div className="vector-component"><span className="vector-label">Tz</span><span className="vector-value">{botaData.tz.toFixed(3)}</span></div>
        </div>
      </div>
    </section>
  );
}
