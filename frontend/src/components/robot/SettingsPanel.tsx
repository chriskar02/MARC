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
  const [standaPort, setStandaPort] = useState("COM1");
  const [loading, setLoading] = useState(false);
  const [networkAdapters, setNetworkAdapters] = useState<NetworkAdapter[]>([]);
  const [selectedAdapter, setSelectedAdapter] = useState<string>("");
  const [mecaAddress, setMecaAddress] = useState<string>("192.168.0.100");

  // Use persistent device store
  const meca500Status = useDeviceStore((state) => state.meca500Status);
  const botaStatus = useDeviceStore((state) => state.botaStatus);

  const setMeca500Status = useDeviceStore((state) => state.setMeca500Status);
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
      <h2>Device Settings &amp; Configuration</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
        {/* ── Basler Cameras ── */}
        <div style={{ borderRight: "1px solid #30363d", paddingRight: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>Basler Cameras</h3>
          <div className="status-display" style={{ marginBottom: "0.75rem" }}>
            <div>Overhead Camera &mdash; <em>overhead_camera</em></div>
            <div>Split Optics Camera &mdash; <em>split_optics_camera</em></div>
            <div>Laser Camera &mdash; <em>laser_camera</em></div>
          </div>
          <p style={{ fontSize: "0.8rem", color: "#8b949e", margin: 0 }}>
            All three Basler cameras start automatically with the backend.
            Camera feeds appear on the Split Optics and Laser &amp; Overhead tabs.
          </p>
        </div>

        {/* ── Standa Stage Motors ── */}
        <div style={{ borderRight: "1px solid #30363d", paddingRight: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>Standa Stage Motors</h3>
          <div className="control-group">
            <label>Serial / USB Port</label>
            <input
              type="text"
              value={standaPort}
              onChange={(e) => setStandaPort(e.target.value)}
              placeholder="COM1, /dev/ttyUSB0, etc."
            />
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("standa_connect", { port: standaPort })} disabled={loading}>
              Connect
            </button>
            <button onClick={() => executeCommand("standa_disconnect")} className="btn-secondary" disabled={loading}>
              Disconnect
            </button>
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("standa_home")} className="btn-secondary" disabled={loading}>
              Home All Axes
            </button>
          </div>
        </div>

        {/* ── Meca500 ── */}
        <div style={{ borderRight: "1px solid #30363d", paddingRight: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>Meca500 Robot Arm</h3>

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

          <div className="control-group">
            <label>Status</label>
            <div className="status-display" style={{ marginTop: "0.5rem", minHeight: "60px" }}>
              {meca500Status ? (
                <>
                  <div>Connected: {meca500Status.connected ? "\u2713" : "\u2717"}</div>
                  {meca500Status.enabled !== undefined && <div>Active: {meca500Status.enabled ? "Yes" : "No"}</div>}
                  {meca500Status.error && <div style={{ color: "#f85149" }}>Error: {meca500Status.error}</div>}
                </>
              ) : (
                <div style={{ color: "#8b949e" }}>No status yet</div>
              )}
            </div>
          </div>
          <div className="control-group">
            <button onClick={() => executeCommand("meca500_activate", { address: mecaAddress })} disabled={loading} title="Activate and home robot">
              Activate &amp; Home
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

        {/* ── Bota MiniONE Pro F/T Sensor ── */}
        <div>
          <h3 style={{ fontSize: "0.95rem", color: "#58a6ff", marginBottom: "1rem" }}>Bota MiniONE Pro F/T Sensor</h3>
          <div className="control-group">
            <label>Status</label>
            <div className="status-display" style={{ marginTop: "0.5rem", minHeight: "60px" }}>
              {botaStatus ? (
                <>
                  <div>Connected: {botaStatus.connected ? "\u2713" : "\u2717"}</div>
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
