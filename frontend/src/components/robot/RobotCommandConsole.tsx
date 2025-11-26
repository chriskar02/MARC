import { useState, useRef, useEffect } from "react";

interface CommandResponse {
  robot?: string;
  pdxc2?: string;
  timestamp?: number;
  error?: string;
}

interface ValveState {
  [key: number]: boolean;
}

export default function RobotCommandConsole() {
  const [command, setCommand] = useState("");
  const [history, setHistory] = useState<Array<{ cmd: string; resp: string }>>();
  const [loading, setLoading] = useState(false);
  const [valveStates, setValveStates] = useState<ValveState>({ 1: false, 2: false });
  const [valveLoading, setValveLoading] = useState<ValveState>({ 1: false, 2: false });
  const historyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [history]);

  const sendCommand = async () => {
    if (!command.trim()) return;

    setLoading(true);
    try {
      const endpoint = "/api/commands/robot";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: command.trim() }),
      });

      const data: CommandResponse = await response.json();
      const responseText = data.error || data.robot || data.pdxc2 || "OK";
      setHistory((prev) => [...(prev || []), { cmd: command, resp: responseText }]);
      setCommand("");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      setHistory((prev) => [...(prev || []), { cmd: command, resp: `ERROR: ${errorMsg}` }]);
      setCommand("");
    } finally {
      setLoading(false);
    }
  };

  const toggleValve = async (valve: number, action: "open" | "close") => {
    setValveLoading((prev) => ({ ...prev, [valve]: true }));
    try {
      const endpoint = action === "open" ? "/api/commands/meca500_valve_open" : "/api/commands/meca500_valve_close";
      await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bank: 1, pin: valve }),
      });
      setValveStates((prev) => ({ ...prev, [valve]: action === "open" }));
    } catch (err) {
      console.error(`Failed to ${action} valve ${valve}:`, err);
    } finally {
      setValveLoading((prev) => ({ ...prev, [valve]: false }));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendCommand();
    }
  };

  return (
    <>
      <h2>Robot Command Console</h2>

      <div
        ref={historyRef}
        className="status-display"
        style={{ flex: 1, marginBottom: "1rem", maxHeight: "300px" }}
      >
        {(history || []).length === 0 ? (
          <div style={{ color: "#8b949e" }}>No commands yet...</div>
        ) : (
          (history || []).map((item, idx) => (
            <div key={idx} style={{ marginBottom: "0.5rem" }}>
              <div style={{ color: "#58a6ff" }}>{"→ " + item.cmd}</div>
              <div style={{ color: "#8b949e" }}>{"← " + item.resp}</div>
            </div>
          ))
        )}
      </div>

      <div className="control-group">
        <label>Command</label>
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter command..."
          disabled={loading}
        />
      </div>

      <div className="control-group">
        <button onClick={sendCommand} disabled={loading || !command.trim()}>
          {loading ? "Sending..." : "Send"}
        </button>
        <button onClick={() => setHistory([])} className="btn-secondary">
          Clear History
        </button>
      </div>

      {/* Pneumatic Valve Controls */}
      <div style={{ marginTop: "1.5rem", borderTop: "1px solid #30363d", paddingTop: "1rem" }}>
        <h3 style={{ marginTop: 0 }}>Pneumatic Valves</h3>
        
        {[1, 2].map((valve) => (
          <div key={valve} className="control-group" style={{ marginBottom: "1rem" }}>
            <label>Valve {valve}: {valveStates[valve] ? "OPEN" : "CLOSED"}</label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={() => toggleValve(valve, "open")}
                disabled={valveLoading[valve] || valveStates[valve]}
                style={{ flex: 1 }}
              >
                {valveLoading[valve] ? "..." : "Open"}
              </button>
              <button
                onClick={() => toggleValve(valve, "close")}
                disabled={valveLoading[valve] || !valveStates[valve]}
                className="btn-secondary"
                style={{ flex: 1 }}
              >
                {valveLoading[valve] ? "..." : "Close"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
