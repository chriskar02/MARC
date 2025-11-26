import { useState } from "react";

interface MotorStatus {
  x_position: number;
  y_position: number;
  x_velocity?: number;
  y_velocity?: number;
}

export default function LaserControl() {
  const [xPos, setXPos] = useState(0);
  const [yPos, setYPos] = useState(0);
  const [xVel, setXVel] = useState(10);
  const [yVel, setYVel] = useState(10);
  const [status, setStatus] = useState<MotorStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const sendCommand = async (command: string, axis: string, value: number) => {
    setLoading(true);
    try {
      const response = await fetch("/api/commands/motors/xy_laser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, axis, value }),
      });
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (err) {
      console.error("Motor command error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <h2>Laser XY Control</h2>

      <div className="control-group">
        <label>X Axis Position (mm)</label>
        <input
          type="number"
          value={xPos}
          onChange={(e) => setXPos(parseFloat(e.target.value))}
          step={0.1}
        />
        <button onClick={() => sendCommand("move", "x", xPos)} disabled={loading}>
          Move X
        </button>
      </div>

      <div className="control-group">
        <label>Y Axis Position (mm)</label>
        <input
          type="number"
          value={yPos}
          onChange={(e) => setYPos(parseFloat(e.target.value))}
          step={0.1}
        />
        <button onClick={() => sendCommand("move", "y", yPos)} disabled={loading}>
          Move Y
        </button>
      </div>

      <div className="control-group">
        <label>X Velocity (mm/s)</label>
        <input
          type="number"
          value={xVel}
          onChange={(e) => setXVel(parseFloat(e.target.value))}
          min={0.1}
          max={50}
          step={0.1}
        />
      </div>

      <div className="control-group">
        <label>Y Velocity (mm/s)</label>
        <input
          type="number"
          value={yVel}
          onChange={(e) => setYVel(parseFloat(e.target.value))}
          min={0.1}
          max={50}
          step={0.1}
        />
      </div>

      <div className="control-group">
        <button onClick={() => sendCommand("home", "", 0)} className="btn-secondary">
          Home XY
        </button>
        <button onClick={() => sendCommand("stop", "", 0)} className="btn-danger">
          Stop
        </button>
      </div>

      {status && (
        <div className="status-display">
          <p>X: {status.x_position.toFixed(2)} mm</p>
          <p>Y: {status.y_position.toFixed(2)} mm</p>
          {status.x_velocity !== undefined && <p>X Vel: {status.x_velocity.toFixed(1)} mm/s</p>}
          {status.y_velocity !== undefined && <p>Y Vel: {status.y_velocity.toFixed(1)} mm/s</p>}
        </div>
      )}
    </section>
  );
}
