import { useState, useRef, useEffect } from "react";
import { useDeviceStore } from "../../stores/deviceStore";

export default function PdxcControl() {
  const [pdxcDistance, setPdxcDistance] = useState<number>(0);
  const [pdxcMode, setPdxcMode] = useState<"open_loop" | "closed_loop">("open_loop");
  const [pdxcLoading, setPdxcLoading] = useState(false);
  const [holdingButton, setHoldingButton] = useState<"left" | "right" | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pdxc2Status = useDeviceStore((state) => state.pdxc2Status);
  const setPdxc2Status = useDeviceStore((state) => state.setPdxc2Status);

  // Handle continuous movement when button is held
  useEffect(() => {
    if (!holdingButton) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Start with a slight delay before continuous movement
    const initialDelay = setTimeout(() => {
      intervalRef.current = setInterval(async () => {
        setPdxcDistance((prev) => {
          const newDistance = holdingButton === "left" ? prev - 1 : prev + 1;
          
          // Send move command immediately
          (async () => {
            setPdxcLoading(true);
            try {
              const command = pdxcMode === "open_loop" ? "pdxc2_move_open_loop" : "pdxc2_move_closed_loop";
              const payload = pdxcMode === "open_loop" 
                ? { step_size: Math.round(newDistance) } 
                : { position: Math.round(newDistance) };
              
              const response = await fetch("/api/commands/device", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command, ...payload }),
              });
              if (response.ok) {
                const data = await response.json();
                setPdxc2Status(data);
              }
            } catch (err) {
              console.error("Move error:", err);
            } finally {
              setPdxcLoading(false);
            }
          })();
          
          return newDistance;
        });
      }, 10); // 10ms per step = 5x faster (was 50ms)
    }, 200); // 200ms initial delay before starting continuous movement

    return () => {
      clearTimeout(initialDelay);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [holdingButton, pdxcMode]);

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
            onMouseDown={() => setHoldingButton("left")}
            onMouseUp={() => setHoldingButton(null)}
            onMouseLeave={() => setHoldingButton(null)}
            disabled={pdxcLoading}
            style={{ 
              padding: "0.4rem 0.6rem", 
              fontSize: "0.85rem",
              backgroundColor: holdingButton === "left" ? "#1f6feb" : undefined,
              cursor: "pointer",
            }}
            title="Hold to move continuously"
          >
            ← Step
          </button>
          <button
            onMouseDown={() => setHoldingButton("right")}
            onMouseUp={() => setHoldingButton(null)}
            onMouseLeave={() => setHoldingButton(null)}
            disabled={pdxcLoading}
            style={{ 
              padding: "0.4rem 0.6rem", 
              fontSize: "0.85rem",
              backgroundColor: holdingButton === "right" ? "#1f6feb" : undefined,
              cursor: "pointer",
            }}
            title="Hold to move continuously"
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
  );
}
