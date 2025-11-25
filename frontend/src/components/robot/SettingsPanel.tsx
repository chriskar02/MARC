import { useState, useEffect } from "react";
import { useDeviceStore } from "../../stores/deviceStore";

interface DeviceStatus {
  connected: boolean;
  active?: boolean;
  enabled?: boolean;
  homed?: boolean;
  current_position?: number;
  position_mode?: string;
  error?: string;
  last_updated?: number;
}

interface NetworkAdapter {
  name: string;
  ip_address: string;
  netmask: string;
  gateway: string;
  meca_address: string;
}

export default function SettingsPanel() {
  const [xyMotorPort, setXyMotorPort] = useState("COM1");
  const [loading, setLoading] = useState(false);
  const [networkAdapters, setNetworkAdapters] = useState<NetworkAdapter[]>([]);
  const [selectedAdapter, setSelectedAdapter] = useState<string>("");
  const [mecaAddress, setMecaAddress] = useState<string>("192.168.0.100");

  // Use persistent device store
  const meca500Status = useDeviceStore((state) => state.meca500Status);
  const pdxc2Status = useDeviceStore((state) => state.pdxc2Status);
  const botaStatus = useDeviceStore((state) => state.botaStatus);

  const setMeca500Status = useDeviceStore((state) => state.setMeca500Status);
  const setPdxc2Status = useDeviceStore((state) => state.setPdxc2Status);
  const setBotaStatus = useDeviceStore((state) => state.setBotaStatus);

  // Load network adapters on mount
  useEffect(() => {
    const loadAdapters = async () => {
      try {
        const response = await fetch("/api/commands/network/adapters");
        const data = await response.json();
        setNetworkAdapters(data.adapters);
        if (data.adapters.length > 0) {
          const first = data.adapters[0];
          setSelectedAdapter(first.name);
          setMecaAddress(first.meca_address);
        }
      } catch (err) {
        console.error("Failed to load network adapters:", err);
      }
    };
    loadAdapters();
  }, []);

  // Update Meca address when adapter changes
  const handleAdapterChange = (adapterName: string) => {
    const adapter = networkAdapters.find((a) => a.name === adapterName);
    if (adapter) {
      setSelectedAdapter(adapterName);
      setMecaAddress(adapter.meca_address);
    }
  };

  const executeCommand = async (command: string, payload: Record<string, unknown> = {}) => {
    setLoading(true);
    try {
      const response = await fetch("/api/commands/device", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, ...payload }),
      });

      if (response.ok) {
        const data = await response.json();
        if (command.includes("meca500")) {
          setMeca500Status(data);
        } else if (command.includes("pdxc2")) {
          setPdxc2Status(data);
        } else if (command.includes("bota")) {
          setBotaStatus(data);
        }
      }
    } catch (err) {
      console.error("Device command error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel" style={{ gridColumn: "1 / -1" }}>
      <h2>Device Settings & Configuration</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
        {/* XY Motors */}
        <div style={{ borderRight: "1px solid #30363d", paddingRight: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>XY Stage Motors</h3>
          <div className="control-group">
            <label>Serial Port</label>
            <input
              type="text"
              value={xyMotorPort}
              onChange={(e) => setXyMotorPort(e.target.value)}
              placeholder="COM1, /dev/ttyUSB0, etc."
            />
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("xy_motors_connect", { port: xyMotorPort })} disabled={loading}>
              Connect
            </button>
            <button onClick={() => executeCommand("xy_motors_disconnect")} className="btn-secondary" disabled={loading}>
              Disconnect
            </button>
          </div>
        </div>

        {/* Meca500 */}
        <div style={{ borderRight: "1px solid #30363d", paddingRight: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>Meca500 Robot Arm</h3>
          
          {/* Network Configuration */}
          <div className="control-group">
            <label>Network Adapter</label>
            <select value={selectedAdapter} onChange={(e) => handleAdapterChange(e.target.value)}>
              <option value="">-- Select Adapter --</option>
              {networkAdapters.map((adapter) => (
                <option key={adapter.name} value={adapter.name}>
                  {adapter.ip_address}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label>Meca500 IP Address</label>
            <input
              type="text"
              value={mecaAddress}
              onChange={(e) => setMecaAddress(e.target.value)}
              placeholder="192.168.0.100"
              title="IP address on same subnet as selected adapter"
            />
          </div>

          {/* Status */}
          <div className="control-group">
            <label>Status</label>
            <div className="status-display" style={{ marginTop: "0.5rem", minHeight: "60px" }}>
              {meca500Status ? (
                <>
                  <div>Connected: {meca500Status.connected ? "✓" : "✗"}</div>
                  {meca500Status.enabled !== undefined && <div>Active: {meca500Status.enabled ? "Yes" : "No"}</div>}
                  {meca500Status.error && <div style={{ color: "#f85149" }}>Error: {meca500Status.error}</div>}
                </>
              ) : (
                <div style={{ color: "#8b949e" }}>No status yet</div>
              )}
            </div>
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("meca500_activate", { address: mecaAddress })} disabled={loading} title="Activate and home robot if needed">
              Activate & Home
            </button>
            <button onClick={() => executeCommand("meca500_deactivate")} className="btn-danger" disabled={loading}>
              Deactivate
            </button>
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("meca500_zero_joints")} className="btn-secondary" disabled={loading}>
              Zero All Joints
            </button>
          </div>
        </div>

        {/* PDXC2 */}
        <div>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>PDXC2 Piezo Stepper</h3>
          
          {/* Connection Status */}
          <div className="control-group">
            <label>Connection Status</label>
            <div className="status-display" style={{ marginTop: "0.5rem", minHeight: "80px", fontSize: "0.9rem" }}>
              {pdxc2Status ? (
                <>
                  <div>Connected: {pdxc2Status.connected ? "✓ Yes" : "✗ No"}</div>
                  <div>Enabled: {pdxc2Status.enabled ? "✓ Yes" : "✗ No"}</div>
                  <div>Homed: {pdxc2Status.homed ? "✓ Yes" : "✗ No"}</div>
                  <div>Position: {pdxc2Status.current_position} {pdxc2Status.position_mode === "closed_loop" ? "nm" : "steps"}</div>
                  {pdxc2Status.error && <div style={{ color: "#f85149", marginTop: "0.5rem" }}>⚠️ {pdxc2Status.error}</div>}
                </>
              ) : (
                <div style={{ color: "#8b949e" }}>Status: Not queried</div>
              )}
            </div>
          </div>

          {/* Connection Controls */}
          <div className="control-group" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <button 
              onClick={() => executeCommand("pdxc2_connect")} 
              disabled={loading} 
              title="Connect to PDXC2 device"
              style={{ fontSize: "0.85rem", padding: "0.4rem 0.6rem" }}
            >
              Connect
            </button>
            <button 
              onClick={() => executeCommand("pdxc2_disconnect")} 
              disabled={loading}
              className="btn-secondary"
              title="Disconnect from device"
              style={{ fontSize: "0.85rem", padding: "0.4rem 0.6rem" }}
            >
              Disconnect
            </button>
          </div>

          {/* Enable/Disable Controls */}
          <div className="control-group" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <button 
              onClick={() => executeCommand("pdxc2_enable")} 
              disabled={loading}
              title="Enable motor (power up stage)"
              style={{ fontSize: "0.85rem", padding: "0.4rem 0.6rem", backgroundColor: "#238636" }}
            >
              Enable
            </button>
            <button 
              onClick={() => executeCommand("pdxc2_disable")} 
              disabled={loading}
              className="btn-danger"
              title="Disable motor (power down)"
              style={{ fontSize: "0.85rem", padding: "0.4rem 0.6rem" }}
            >
              Disable
            </button>
          </div>

          {/* Calibration/Homing */}
          <div className="control-group" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <button 
              onClick={() => executeCommand("pdxc2_calibrate")} 
              disabled={loading}
              title="Run encoder optimization and homing routine"
              style={{ fontSize: "0.85rem", padding: "0.4rem 0.6rem" }}
            >
              Calibrate
            </button>
            <button 
              onClick={() => executeCommand("pdxc2_home")} 
              disabled={loading}
              className="btn-secondary"
              title="Home stage (set encoder reference)"
              style={{ fontSize: "0.85rem", padding: "0.4rem 0.6rem" }}
            >
              Home
            </button>
          </div>
        </div>

        {/* Bota Sensor */}
        <div style={{ gridColumn: "1 / -1", borderTop: "1px solid #30363d", paddingTop: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>Bota MiniONE Pro F/T Sensor</h3>
          <div className="control-group">
            <label>Status</label>
            <div className="status-display" style={{ marginTop: "0.5rem", minHeight: "60px" }}>
              {botaStatus ? (
                <>
                  <div>Connected: {botaStatus.connected ? "✓" : "✗"}</div>
                  {botaStatus.error && <div style={{ color: "#f85149" }}>Error: {botaStatus.error}</div>}
                </>
              ) : (
                <div style={{ color: "#8b949e" }}>No status yet</div>
              )}
            </div>
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("bota_tare")} disabled={loading} title="Zero sensor readings">
              Tare Sensor
            </button>
            <button onClick={() => executeCommand("bota_reconnect")} className="btn-secondary" disabled={loading}>
              Reconnect
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
