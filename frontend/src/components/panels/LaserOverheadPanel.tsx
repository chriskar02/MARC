import { useState } from "react";
import CameraStream from "../camera/CameraStream";

/**
 * Panel 2 – Laser & Overhead
 *  • Laser camera feed              (Basler)  [disabled — no 3rd camera]
 *  • Stage XYZ controls              (Standa motors, XILab-style arrows)
 *  • Overhead camera feed            (Basler)
 */
export default function LaserOverheadPanel() {
  /* ── Standa Stage XYZ ─────────────────────────────── */
  const [stageStep, setStageStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const stageMove = async (axis: string, delta: number) => {
    setLoading(true);
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "standa_move", axis, value: delta }),
      });
    } catch (err) {
      console.error("Standa move failed", err);
    } finally {
      setLoading(false);
    }
  };

  const stageHome = async () => {
    setLoading(true);
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "standa_home" }),
      });
    } catch (err) {
      console.error("Home failed", err);
    } finally {
      setLoading(false);
    }
  };

  const stageStop = async () => {
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "standa_stop" }),
      });
    } catch (err) {
      console.error("Stop failed", err);
    }
  };

  return (
    <div className="laser-overhead-layout">
      {/* ── Left column: Laser camera + Stage controls ── */}
      <div className="controls-column">
        {/* Laser Camera placeholder (disabled) */}
        <section className="panel" style={{ flex: 1, opacity: 0.5 }}>
          <h2>Laser Camera (not connected)</h2>
          <div style={{ padding: "2rem", textAlign: "center", color: "#8b949e", border: "1px dashed #30363d", borderRadius: 8 }}>
            No third Basler camera detected.
          </div>
        </section>

        {/* Stage XYZ Controls (Standa) — XILab arrows */}
        <section className="panel">
          <h2>Stage XYZ Controls (Standa)</h2>

          <div className="control-group">
            <label>Step (mm)</label>
            <input type="number" value={stageStep} min={0.001} step={0.1}
              onChange={(e) => setStageStep(parseFloat(e.target.value) || 0.1)}
              style={{ width: "100%" }} />
          </div>

          <div className="arrow-pad-container">
            {/* XY cross */}
            <div className="arrow-cross">
              <button className="arrow-btn arrow-up" onClick={() => stageMove("y", stageStep)} disabled={loading} title="+Y">
                <span className="arrow-icon">&#9650;</span><span className="arrow-axis">Y+</span>
              </button>
              <button className="arrow-btn arrow-left" onClick={() => stageMove("x", -stageStep)} disabled={loading} title="-X">
                <span className="arrow-icon">&#9664;</span><span className="arrow-axis">X−</span>
              </button>
              <div className="arrow-center">XY</div>
              <button className="arrow-btn arrow-right" onClick={() => stageMove("x", stageStep)} disabled={loading} title="+X">
                <span className="arrow-icon">&#9654;</span><span className="arrow-axis">X+</span>
              </button>
              <button className="arrow-btn arrow-down" onClick={() => stageMove("y", -stageStep)} disabled={loading} title="-Y">
                <span className="arrow-icon">&#9660;</span><span className="arrow-axis">Y−</span>
              </button>
            </div>
            {/* Z column */}
            <div className="arrow-z-col">
              <button className="arrow-btn arrow-z-up" onClick={() => stageMove("z", stageStep)} disabled={loading} title="+Z">
                <span className="arrow-icon">&#9650;</span><span className="arrow-axis">Z+</span>
              </button>
              <div className="arrow-center">Z</div>
              <button className="arrow-btn arrow-z-down" onClick={() => stageMove("z", -stageStep)} disabled={loading} title="-Z">
                <span className="arrow-icon">&#9660;</span><span className="arrow-axis">Z−</span>
              </button>
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
            <button onClick={stageHome} className="btn-secondary" disabled={loading} style={{ flex: 1 }}>Home</button>
            <button onClick={stageStop} className="btn-danger" style={{ flex: 1 }}>Stop</button>
          </div>
        </section>
      </div>

      {/* ── Right column: Overhead camera ── */}
      <div className="camera-column">
        <section className="panel" style={{ flex: 1 }}>
          <CameraStream workerName="overhead_camera" />
        </section>
      </div>
    </div>
  );
}
