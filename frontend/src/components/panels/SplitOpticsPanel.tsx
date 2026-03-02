import { useState, useEffect, useCallback } from "react";
import CameraStream from "../camera/CameraStream";
import BotaFeedback from "../sensors/BotaFeedback";

/**
 * Panel 1 – Split Optics
 *
 * Layout (no scroll):
 *  ┌───────────────────────────────────────────────┐
 *  │ TOP BAR: Standa XY (per-axis step) │ Stage Z  │
 *  ├──────────────────┬────────────────────────────┤
 *  │ LEFT: Meca500    │ RIGHT: Split Optics Camera │
 *  │ per-axis steps   │                            │
 *  │ XY+Z arrow pads  │                            │
 *  │ Absolute go-to   │                            │
 *  │ Bota F/T readout │                            │
 *  └──────────────────┴────────────────────────────┘
 */
export default function SplitOpticsPanel() {
  /* ── Meca connection state ─────────────────────────── */
  const [mecaConnected, setMecaConnected] = useState(false);

  /* ── Meca pose polling ─────────────────────────────── */
  const [pose, setPose] = useState<{ x: number; y: number; z: number; alpha: number; beta: number; gamma: number } | null>(null);

  const pollPose = useCallback(async () => {
    try {
      const res = await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_get_pose" }),
      });
      if (res.ok) {
        const data = await res.json();
        setMecaConnected(!!data.connected);
        if (data.pose) setPose(data.pose);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    pollPose();
    const id = setInterval(pollPose, 1000);
    return () => clearInterval(id);
  }, [pollPose]);

  const [mecaPortalUrl, setMecaPortalUrl] = useState<string | null>(null);

  const mecaActivate = async () => {
    setMecaLoading(true);
    setMecaError(null);
    setMecaPortalUrl(null);
    try {
      const res = await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_activate", address: "192.168.0.100" }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.error) {
          setMecaError(data.error);
          if (data.portal_url) setMecaPortalUrl(data.portal_url);
        }
        setMecaConnected(!!data.connected && !!data.enabled);
      }
      await pollPose();
    } catch (err) {
      console.error("Meca activate failed", err);
      setMecaError(String(err));
    } finally {
      setMecaLoading(false);
    }
  };

  /* ── Meca XYZ (per-axis steps) ─────────────────────── */
  const [mecaStepX, setMecaStepX] = useState<number>(1);
  const [mecaStepY, setMecaStepY] = useState<number>(1);
  const [mecaStepZ, setMecaStepZ] = useState<number>(1);
  const [mecaLoading, setMecaLoading] = useState(false);
  const [mecaTarget, setMecaTarget] = useState({ x: 0, y: 0, z: 0 });
  const [mecaError, setMecaError] = useState<string | null>(null);

  const mecaDisabled = mecaLoading || !mecaConnected;

  const mecaDelta = async (dx: number, dy: number, dz: number) => {
    setMecaLoading(true);
    setMecaError(null);
    try {
      const res = await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_move_xyz_delta", dx, dy, dz }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.error) setMecaError(data.error);
      }
      await pollPose();
    } catch (err) {
      console.error("Meca delta move failed", err);
      setMecaError(String(err));
    } finally {
      setMecaLoading(false);
    }
  };

  const mecaGoTo = async () => {
    setMecaLoading(true);
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_move_pose", ...mecaTarget }),
      });
      await pollPose();
    } catch (err) {
      console.error("Meca absolute move failed", err);
    } finally {
      setMecaLoading(false);
    }
  };

  /* ── Standa Split-optics XY (per-axis steps) ───────── */
  const [standaStepX, setStandaStepX] = useState(0.1);
  const [standaStepY, setStandaStepY] = useState(0.1);
  const [standaLoading, setStandaLoading] = useState(false);

  const standaMove = async (axis: string, value: number) => {
    setStandaLoading(true);
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "standa_move", axis, value }),
      });
    } catch (err) {
      console.error("Standa move failed", err);
    } finally {
      setStandaLoading(false);
    }
  };

  /* ── Standa Stage Z ────────────────────────────────── */
  const [stageZ, setStageZ] = useState(0);
  const [stageZStep, setStageZStep] = useState(0.1);
  const [zLoading, setZLoading] = useState(false);

  const stageZMove = async (value: number) => {
    setZLoading(true);
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "standa_move", axis: "z", value }),
      });
      setStageZ(value);
    } catch (err) {
      console.error("Stage Z move failed", err);
    } finally {
      setZLoading(false);
    }
  };

  return (
    <div className="split-optics-layout">

      {/* ═══════════ TOP BAR: Standa XY + Stage Z ═══════════ */}
      <div className="so-top-bar">
        {/* ── Standa XY ── */}
        <section className="panel so-standa-xy">
          <h2>Split Optics XY (Standa)</h2>
          <div className="so-top-inner">
            <div className="arrow-cross arrow-cross-sm">
              <button className="arrow-btn arrow-btn-sm arrow-up" onClick={() => standaMove("y", standaStepY)} disabled={standaLoading} title="+Y">
                <span className="arrow-icon">&#9650;</span><span className="arrow-axis">Y+</span>
              </button>
              <button className="arrow-btn arrow-btn-sm arrow-left" onClick={() => standaMove("x", -standaStepX)} disabled={standaLoading} title="-X">
                <span className="arrow-icon">&#9664;</span><span className="arrow-axis">X−</span>
              </button>
              <div className="arrow-center arrow-center-sm">XY</div>
              <button className="arrow-btn arrow-btn-sm arrow-right" onClick={() => standaMove("x", standaStepX)} disabled={standaLoading} title="+X">
                <span className="arrow-icon">&#9654;</span><span className="arrow-axis">X+</span>
              </button>
              <button className="arrow-btn arrow-btn-sm arrow-down" onClick={() => standaMove("y", -standaStepY)} disabled={standaLoading} title="-Y">
                <span className="arrow-icon">&#9660;</span><span className="arrow-axis">Y−</span>
              </button>
            </div>
            <div className="step-col">
              <label className="step-label">X step (mm)</label>
              <input type="number" className="step-input" value={standaStepX} min={0.001} step={0.01}
                onChange={(e) => setStandaStepX(parseFloat(e.target.value) || 0.01)} />
              <label className="step-label">Y step (mm)</label>
              <input type="number" className="step-input" value={standaStepY} min={0.001} step={0.01}
                onChange={(e) => setStandaStepY(parseFloat(e.target.value) || 0.01)} />
            </div>
          </div>
        </section>

        {/* ── Stage Z ── */}
        <section className="panel so-stage-z">
          <h2>Stage Z (Standa)</h2>
          <div className="so-top-inner">
            <div className="arrow-z-col">
              <button className="arrow-btn arrow-btn-sm arrow-z-up" onClick={() => stageZMove(stageZ + stageZStep)} disabled={zLoading} title="+Z">
                <span className="arrow-icon">&#9650;</span><span className="arrow-axis">Z+</span>
              </button>
              <div className="arrow-center arrow-center-sm">{stageZ.toFixed(3)}</div>
              <button className="arrow-btn arrow-btn-sm arrow-z-down" onClick={() => stageZMove(stageZ - stageZStep)} disabled={zLoading} title="-Z">
                <span className="arrow-icon">&#9660;</span><span className="arrow-axis">Z−</span>
              </button>
            </div>
            <div className="step-col">
              <label className="step-label">Z step (mm)</label>
              <input type="number" className="step-input" value={stageZStep} min={0.001} step={0.01}
                onChange={(e) => setStageZStep(parseFloat(e.target.value) || 0.01)} />
            </div>
          </div>
        </section>
      </div>

      {/* ═══════════ BOTTOM LEFT: Meca500 + Bota ═══════════ */}
      <div className="so-left-col">
        <section className="panel">
          <h2>Meca500 XYZ Control</h2>

          {/* Connection indicator + activate */}
          {!mecaConnected ? (
            <div style={{ marginBottom: "0.5rem" }}>
              <span style={{ color: "#da3633", fontSize: "0.8rem", marginRight: "0.5rem" }}>&#x25CF; Disconnected</span>
              <button onClick={mecaActivate} disabled={mecaLoading} style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}>
                {mecaLoading ? "Connecting…" : "Activate & Home"}
              </button>
              {mecaError && (
                <div style={{ color: "#f85149", fontSize: "0.75rem", marginTop: "0.25rem", lineHeight: 1.3 }}>
                  {mecaError}
                  {mecaPortalUrl && (
                    <> — <a href={mecaPortalUrl} target="_blank" rel="noreferrer"
                        style={{ color: "#58a6ff", textDecoration: "underline" }}>
                        Open MecaPortal
                      </a>
                    </>
                  )}
                </div>
              )}
            </div>
          ) : (
            <span style={{ color: "#3fb950", fontSize: "0.8rem", marginBottom: "0.5rem", display: "block" }}>&#x25CF; Connected</span>
          )}

          {/* Pose readout */}
          <div className="xyz-readout">
            <div className="xyz-item"><span className="xyz-label">X</span><span className="xyz-value">{pose?.x?.toFixed(3) ?? "--"}</span></div>
            <div className="xyz-item"><span className="xyz-label">Y</span><span className="xyz-value">{pose?.y?.toFixed(3) ?? "--"}</span></div>
            <div className="xyz-item"><span className="xyz-label">Z</span><span className="xyz-value">{pose?.z?.toFixed(3) ?? "--"}</span></div>
          </div>

          {/* Per-axis step sizes */}
          <div className="step-row">
            <div><label className="step-label">X step</label><input type="number" className="step-input" value={mecaStepX} min={0.01} step={0.1} onChange={(e) => setMecaStepX(parseFloat(e.target.value) || 0.1)} /></div>
            <div><label className="step-label">Y step</label><input type="number" className="step-input" value={mecaStepY} min={0.01} step={0.1} onChange={(e) => setMecaStepY(parseFloat(e.target.value) || 0.1)} /></div>
            <div><label className="step-label">Z step</label><input type="number" className="step-input" value={mecaStepZ} min={0.01} step={0.1} onChange={(e) => setMecaStepZ(parseFloat(e.target.value) || 0.1)} /></div>
          </div>

          {/* Error display */}
          {mecaError && <div style={{ color: "#f85149", fontSize: "0.75rem", marginBottom: "0.25rem" }}>{mecaError}</div>}

          {/* XILab-style arrow pad: XY + Z */}
          <div className="arrow-pad-container">
            <div className="arrow-cross arrow-cross-sm">
              <button className="arrow-btn arrow-btn-sm arrow-up" onClick={() => mecaDelta(0, mecaStepY, 0)} disabled={mecaDisabled} title="+Y">
                <span className="arrow-icon">&#9650;</span><span className="arrow-axis">Y+</span>
              </button>
              <button className="arrow-btn arrow-btn-sm arrow-left" onClick={() => mecaDelta(-mecaStepX, 0, 0)} disabled={mecaDisabled} title="-X">
                <span className="arrow-icon">&#9664;</span><span className="arrow-axis">X−</span>
              </button>
              <div className="arrow-center arrow-center-sm">XY</div>
              <button className="arrow-btn arrow-btn-sm arrow-right" onClick={() => mecaDelta(mecaStepX, 0, 0)} disabled={mecaDisabled} title="+X">
                <span className="arrow-icon">&#9654;</span><span className="arrow-axis">X+</span>
              </button>
              <button className="arrow-btn arrow-btn-sm arrow-down" onClick={() => mecaDelta(0, -mecaStepY, 0)} disabled={mecaDisabled} title="-Y">
                <span className="arrow-icon">&#9660;</span><span className="arrow-axis">Y−</span>
              </button>
            </div>
            <div className="arrow-z-col">
              <button className="arrow-btn arrow-btn-sm arrow-z-up" onClick={() => mecaDelta(0, 0, mecaStepZ)} disabled={mecaDisabled} title="+Z">
                <span className="arrow-icon">&#9650;</span><span className="arrow-axis">Z+</span>
              </button>
              <div className="arrow-center arrow-center-sm">Z</div>
              <button className="arrow-btn arrow-btn-sm arrow-z-down" onClick={() => mecaDelta(0, 0, -mecaStepZ)} disabled={mecaDisabled} title="-Z">
                <span className="arrow-icon">&#9660;</span><span className="arrow-axis">Z−</span>
              </button>
            </div>
          </div>

          {/* Absolute go-to */}
          <div className="step-row" style={{ marginTop: "0.5rem" }}>
            <div><label className="step-label">X</label><input type="number" className="step-input" value={mecaTarget.x} step={0.1} onChange={(e) => setMecaTarget(p => ({ ...p, x: parseFloat(e.target.value) || 0 }))} /></div>
            <div><label className="step-label">Y</label><input type="number" className="step-input" value={mecaTarget.y} step={0.1} onChange={(e) => setMecaTarget(p => ({ ...p, y: parseFloat(e.target.value) || 0 }))} /></div>
            <div><label className="step-label">Z</label><input type="number" className="step-input" value={mecaTarget.z} step={0.1} onChange={(e) => setMecaTarget(p => ({ ...p, z: parseFloat(e.target.value) || 0 }))} /></div>
          </div>
          <button onClick={mecaGoTo} disabled={mecaDisabled} style={{ width: "100%", marginTop: "0.25rem" }}>
            {mecaLoading ? "Moving…" : "Go to Position"}
          </button>
        </section>

        <BotaFeedback />
      </div>

      {/* ═══════════ BOTTOM RIGHT: Camera ═══════════ */}
      <div className="so-right-col">
        <section className="panel" style={{ flex: 1, minHeight: 0 }}>
          <CameraStream workerName="split_optics_camera" />
        </section>
      </div>
    </div>
  );
}
