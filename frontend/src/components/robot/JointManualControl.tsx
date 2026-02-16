import { useRef, useState } from "react";
import { useChannel } from "../../hooks/useChannel";
import CameraStream from "../camera/CameraStream";

interface RobotState {
  joint_angles: [number, number, number, number, number, number];
  pose: { x: number; y: number; z: number; alpha: number; beta: number; gamma: number };
  is_moving: boolean;
}

export default function JointManualControl() {
  const robotState = useChannel<RobotState>("robot/state");

  const [joints, setJoints] = useState<[number, number, number, number, number, number]>([0, 0, 0, 0, 0, 0]);
  const sendTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const jointNames = ["Joint 1", "Joint 2", "Joint 3", "Joint 4", "Joint 5", "Joint 6"];
  const jointLimits = [
    [-90, 90],
    [-90, 90],
    [-90, 90],
    [-180, 180],
    [-180, 180],
    [-180, 180],
  ] as const;

  const sendMoveJoints = async (angles: [number, number, number, number, number, number]) => {
    // Send joints as a device-level command
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_move_joints", angles }),
      });
    } catch (err) {
      console.error("Failed to send move_joints", err);
    }
  };

  const updateJointLocal = (idx: number, value: number) => {
    const newJoints: [number, number, number, number, number, number] = [...joints] as any;
    newJoints[idx] = value;
    setJoints(newJoints);

    if (sendTimeoutRef.current) {
      clearTimeout(sendTimeoutRef.current);
    }
    sendTimeoutRef.current = setTimeout(() => {
      sendMoveJoints(newJoints);
    }, 150);
  };

  const sendShippingPosition = async () => {
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_move_shipping" }),
      });
    } catch (err) {
      console.error("Failed to send shipping position", err);
    }
  };

  const sendPickPlacePosition = () => {
    const pickPlaceJoints: [number, number, number, number, number, number] = [30, 20, 70, 0, -90, 0];
    setJoints(pickPlaceJoints);
    if (sendTimeoutRef.current) {
      clearTimeout(sendTimeoutRef.current);
      sendTimeoutRef.current = null;
    }
    sendMoveJoints(pickPlaceJoints);
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
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
              <input
                type="range"
                min={jointLimits[idx][0]}
                max={jointLimits[idx][1]}
                step={0.1}
                value={angle}
                onChange={(e) => updateJointLocal(idx, parseFloat(e.target.value) || 0)}
                style={{ flex: 1 }}
              />
              <input
                type="number"
                min={jointLimits[idx][0]}
                max={jointLimits[idx][1]}
                step={0.1}
                value={angle}
                onChange={(e) => updateJointLocal(idx, parseFloat(e.target.value) || 0)}
                style={{ width: "6rem" }}
              />
            </div>
          </div>
        ))}

        <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", flexWrap: "wrap" }}>
          <button onClick={() => sendMoveJoints(joints)}>Move Joints</button>
          <button onClick={sendPickPlacePosition} className="btn-secondary">
            Pick & Place Pose
          </button>
          <button onClick={sendShippingPosition} className="btn-secondary">
            Shipping Position
          </button>
        </div>
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

      {/* Camera Feed */}
      <div style={{ borderTop: "1px solid #30363d", paddingTop: "1rem" }}>
        <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>
          Camera Feed
        </h3>
        <div style={{ maxHeight: "250px", overflow: "hidden", borderRadius: "4px" }}>
          <CameraStream workerName="basler_camera" />
        </div>
      </div>
    </>
  );
}
