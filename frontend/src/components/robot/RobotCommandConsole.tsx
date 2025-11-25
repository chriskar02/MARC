import { useState, useRef, useEffect } from "react";

interface CommandResponse {
  robot?: string;
  pdxc2?: string;
  timestamp?: number;
  error?: string;
}

export default function RobotCommandConsole() {
  const [command, setCommand] = useState("");
  const [history, setHistory] = useState<Array<{ cmd: string; resp: string }>>([]);
  const [target, setTarget] = useState<"robot" | "pdxc2">("robot");
  const [loading, setLoading] = useState(false);
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
      const endpoint = target === "robot" ? "/api/commands/robot" : "/api/commands/pdxc2";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: command.trim() }),
      });

      const data: CommandResponse = await response.json();
      const responseText = data.error || data.robot || data.pdxc2 || "OK";
      setHistory((prev) => [...prev, { cmd: command, resp: responseText }]);
      setCommand("");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      setHistory((prev) => [...prev, { cmd: command, resp: `ERROR: ${errorMsg}` }]);
      setCommand("");
    } finally {
      setLoading(false);
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

      <div className="control-group">
        <label>Target</label>
        <select value={target} onChange={(e) => setTarget(e.target.value as "robot" | "pdxc2")}>
          <option value="robot">Meca500 Robot</option>
          <option value="pdxc2">PDXC2 Piezo</option>
        </select>
      </div>

      <div
        ref={historyRef}
        className="status-display"
        style={{ flex: 1, marginBottom: "1rem", maxHeight: "300px" }}
      >
        {history.length === 0 ? (
          <div style={{ color: "#8b949e" }}>No commands yet...</div>
        ) : (
          history.map((item, idx) => (
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
    </>
  );
}
