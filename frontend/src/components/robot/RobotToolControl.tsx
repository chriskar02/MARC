import { useState } from "react";
import { useChannel } from "../../hooks/useChannel";

interface RobotState {
  joint_angles: [number, number, number, number, number, number];
  pose: { x: number; y: number; z: number; alpha: number; beta: number; gamma: number };
  is_moving: boolean;
}

export default function RobotToolControl() {
  const robotState = useChannel<RobotState>("robot/state");
  const [step, setStep] = useState<number>(1);
  const [cachedJoints, setCachedJoints] = useState<[number, number, number, number, number, number] | null>(null);

  const hasValidPose = (pose?: RobotState["pose"]) => {
    if (!pose) return false;
    return (
      typeof pose.x === "number" &&
      typeof pose.y === "number" &&
      typeof pose.z === "number" &&
      typeof pose.alpha === "number" &&
      typeof pose.beta === "number" &&
      typeof pose.gamma === "number"
    );
  };

  const applyRobotConstraints = (
    joints: [number, number, number, number, number, number]
  ): [number, number, number, number, number, number] => {
    const constrained = [...joints] as [number, number, number, number, number, number];
    constrained[4] = -90;
    const sum = constrained[1] + constrained[2];
    const correction = (sum - 90) / 2;
    constrained[1] -= correction;
    constrained[2] -= correction;
    return constrained;
  };

  const sendMoveJoints = async (joints: [number, number, number, number, number, number]) => {
    try {
      await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: "meca500_move_joints", angles: joints }),
      });
    } catch (err) {
      console.error("Move joints failed", err);
    }
  };

  const getBaseJoints = (): [number, number, number, number, number, number] => {
    if (Array.isArray(robotState?.joint_angles) && robotState.joint_angles.length === 6) {
      return robotState.joint_angles;
    }
    if (cachedJoints) {
      return cachedJoints;
    }
    return [0, 0, 0, 0, -90, 0];
  };

  const sendJointDelta = async (dx: number, dy: number, dz: number) => {
    const base = getBaseJoints();
    const next: [number, number, number, number, number, number] = [...base] as any;
    next[0] += dx;
    next[1] += dy;
    next[2] += dz;
    const constrained = applyRobotConstraints(next);
    setCachedJoints(constrained);
    await sendMoveJoints(constrained);
  };

  const sendPickPlacePosition = async () => {
    const pickPlace: [number, number, number, number, number, number] = [30, 20, 70, 0, -90, 0];
    const constrained = applyRobotConstraints(pickPlace);
    setCachedJoints(constrained);
    await sendMoveJoints(constrained);
  };

  return (
    <>
      <h2>Robot Tool Control</h2>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexDirection: "column" }}>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <label>Step (deg)</label>
          <input type="number" value={step} onChange={(e) => setStep(parseFloat(e.target.value) || 0)} style={{ width: "6rem" }} />
          <button className="btn-secondary" onClick={sendPickPlacePosition}>
            Pick & Place Pose
          </button>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <button onClick={() => sendJointDelta(0, step, 0)}>+Y</button>
            <button onClick={() => sendJointDelta(0, -step, 0)} className="btn-secondary">-Y</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <button onClick={() => sendJointDelta(step, 0, 0)}>+X</button>
            <button onClick={() => sendJointDelta(-step, 0, 0)} className="btn-secondary">-X</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <button onClick={() => sendJointDelta(0, 0, step)}>+Z</button>
            <button onClick={() => sendJointDelta(0, 0, -step)} className="btn-secondary">-Z</button>
          </div>
        </div>

        {hasValidPose(robotState?.pose) && (
          <div style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
            <div>Pose: x={robotState.pose.x.toFixed(2)} y={robotState.pose.y.toFixed(2)} z={robotState.pose.z.toFixed(2)}</div>
            <div>Orientation: α={robotState.pose.alpha.toFixed(2)} β={robotState.pose.beta.toFixed(2)} γ={robotState.pose.gamma.toFixed(2)}</div>
          </div>
        )}
      </div>
    </>
  );
}
