import { useState } from "react";
import { useChannel } from "../../hooks/useChannel";
import { useWebSocketContext } from "../../providers/WebSocketProvider";
import { useDeviceStore } from "../../stores/deviceStore";

interface RobotState {
  joint_angles: [number, number, number, number, number, number];
  pose: { x: number; y: number; z: number; alpha: number; beta: number; gamma: number };
  is_moving: boolean;
}

export default function JointManualControl() {
  const robotState = useChannel<RobotState>("robot/state");
  const { send } = useWebSocketContext();

  const [joints, setJoints] = useState<[number, number, number, number, number, number]>([0, 0, 0, 0, 0, 0]);
  const [pdxcDistance, setPdxcDistance] = useState<number>(0);
  const [pdxcMode, setPdxcMode] = useState<"open_loop" | "closed_loop">("open_loop");
  const [pdxcLoading, setPdxcLoading] = useState(false);

  const pdxc2Status = useDeviceStore((state) => state.pdxc2Status);
  const setPdxc2Status = useDeviceStore((state) => state.setPdxc2Status);

  const jointNames = ["Joint 1", "Joint 2", "Joint 3", "Joint 4", "Joint 5", "Joint 6"];
  const jointLimits = [
    [-90, 90],
    [-90, 90],
    [-90, 90],
    [-180, 180],
    [-180, 180],
    [-180, 180],
  ] as const;

  const sendJointCommand = (idx: number, value: number) => {
    const newJoints: [number, number, number, number, number, number] = [...joints] as any;
    newJoints[idx] = value;
    setJoints(newJoints);
    send?.({
      type: "robot_command",
      command: "move_joints",
      angles: newJoints,
    });
  };

  const sendPdxcMove = async () => {
    setPdxcLoading(true);
    try {
      const command = pdxcMode === "open_loop" ? "pdxc2_move_open_loop" : "pdxc2_move_closed_loop";
      const payload = pdxcMode === "open_loop" ? { step_size: Math.round(pdxcDistance) } : { position: Math.round(pdxcDistance) };
      
      const response = await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, ...payload }),
      });
      if (response.ok) {
        const data = await response.json();
        setPdxc2Status(data);
      } else {
        console.error("Move command failed");
      }
    } catch (err) {
      console.error("Move error:", err);
    } finally {
      setPdxcLoading(false);
    }
  };

  const changePdxcMode = async (mode: "open_loop" | "closed_loop") => {
    setPdxcLoading(true);
    try {
      const command = mode === "open_loop" ? "pdxc2_set_open_loop" : "pdxc2_set_closed_loop";
      const response = await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      if (response.ok) {
        const data = await response.json();
        setPdxc2Status(data);
        setPdxcMode(mode);
      }
    } catch (err) {
      console.error("Mode change error:", err);
    } finally {
      setPdxcLoading(false);
    }
  };

  return (
    <>
      <h2>Manual Joint Control</h2>

      <div style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>
          Meca500 (6 Axes)
        </h3>
        {joints.map((angle, idx) => (
          <div key={idx} className="slider-group">
            <label>
              <span>{jointNames[idx]}</span>
              <span className="slider-value">{angle.toFixed(1)}°</span>
            </label>
            <input
              type="range"
              min={jointLimits[idx][0]}
              max={jointLimits[idx][1]}
              step={0.5}
              value={angle}
              onChange={(e) => sendJointCommand(idx, parseFloat(e.target.value))}
            />
          </div>
        ))}
        {robotState && (
          <div className="status-display" style={{ marginTop: "1rem" }}>
            <div style={{ fontSize: "0.75rem" }}>Current Angles:</div>
            {robotState.joint_angles.map((ang: number, idx: number) => (
              <div key={idx} style={{ fontSize: "0.75rem" }}>
                Joint {idx + 1}: {ang.toFixed(2)}°
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ borderTop: "1px solid #30363d", paddingTop: "1rem" }}>
        <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>
          PDXC2 Piezo Stepper
        </h3>

        {/* Mode Selection */}
        <div className="control-group">
          <label>Control Mode</label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <button
              onClick={() => changePdxcMode("open_loop")}
              disabled={pdxcLoading}
              style={{
                fontSize: "0.85rem",
                padding: "0.4rem 0.6rem",
                backgroundColor: pdxcMode === "open_loop" ? "#238636" : undefined,
              }}
              title="Fast stepper control (no feedback)"
            >
              Open Loop {pdxcMode === "open_loop" ? "✓" : ""}
            </button>
            <button
              onClick={() => changePdxcMode("closed_loop")}
              disabled={pdxcLoading}
              style={{
                fontSize: "0.85rem",
                padding: "0.4rem 0.6rem",
                backgroundColor: pdxcMode === "closed_loop" ? "#238636" : undefined,
              }}
              title="Encoder feedback control (precise)"
            >
              Closed Loop {pdxcMode === "closed_loop" ? "✓" : ""}
            </button>
          </div>
        </div>

        {/* Distance Input */}
        <div className="control-group">
          <label>
            Distance {pdxcMode === "open_loop" ? "(steps)" : "(nm)"}
          </label>
          <input
            type="number"
            value={pdxcDistance}
            onChange={(e) => setPdxcDistance(parseFloat(e.target.value))}
            placeholder={pdxcMode === "open_loop" ? "Step count (negative allowed)" : "Position (nm)"}
            style={{ width: "100%", marginBottom: "0.5rem" }}
          />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <button
              onClick={() => setPdxcDistance(pdxcDistance - 1)}
              disabled={pdxcLoading}
              style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}
              title="Decrease by 1"
            >
              ← Step
            </button>
            <button
              onClick={() => setPdxcDistance(pdxcDistance + 1)}
              disabled={pdxcLoading}
              style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}
              title="Increase by 1"
            >
              Step →
            </button>
          </div>
          <button
            onClick={sendPdxcMove}
            disabled={pdxcLoading}
            style={{ width: "100%", padding: "0.5rem", marginTop: "0.5rem" }}
          >
            {pdxcLoading ? "Moving..." : "Move"}
          </button>
        </div>

        {/* Status Display */}
        {pdxc2Status && (
          <div className="status-display" style={{ marginTop: "1rem", fontSize: "0.9rem" }}>
            <div>Connected: {pdxc2Status.connected ? "✓ Yes" : "✗ No"}</div>
            <div>Enabled: {pdxc2Status.enabled ? "✓ Yes" : "✗ No"}</div>
            <div>Position: {pdxc2Status.current_position} {pdxcMode === "closed_loop" ? "nm" : "steps"}</div>
            {pdxc2Status.error && <div style={{ color: "#f85149" }}>⚠️ {pdxc2Status.error}</div>}
          </div>
        )}
      </div>
    </>
  );
}
