import { useState } from "react";
import { useChannel } from "../../hooks/useChannel";
import { useWebSocketContext } from "../../providers/WebSocketProvider";
import CameraStream from "../camera/CameraStream";

interface RobotState {
  joint_angles: [number, number, number, number, number, number];
  pose: { x: number; y: number; z: number; alpha: number; beta: number; gamma: number };
  is_moving: boolean;
}

export default function JointManualControl() {
  const robotState = useChannel<RobotState>("robot/state");
  const { send } = useWebSocketContext();

  const [joints, setJoints] = useState<[number, number, number, number, number, number]>([0, 0, 0, 0, 0, 0]);

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
