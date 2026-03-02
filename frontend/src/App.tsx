import { useState } from "react";
import { useChannel } from "./hooks/useChannel";
import SplitOpticsPanel from "./components/panels/SplitOpticsPanel";
import LaserOverheadPanel from "./components/panels/LaserOverheadPanel";
import SettingsPanel from "./components/robot/SettingsPanel";

export default function App() {
  const heartbeat = useChannel("telemetry/realtime");
  const [activeTab, setActiveTab] = useState<"split_optics" | "laser_overhead" | "settings">("split_optics");

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>
          <span style={{ fontSize: "2rem" }}>M</span>
          <span style={{ fontSize: "1.2rem" }}>ATEL</span>
          <span style={{ fontSize: "2rem" }}> A</span>
          <span style={{ fontSize: "1.2rem" }}>utomated</span>
          <span style={{ fontSize: "2rem" }}> R</span>
          <span style={{ fontSize: "1.2rem" }}>obot</span>
          <span style={{ fontSize: "2rem" }}> C</span>
          <span style={{ fontSize: "1.2rem" }}>ontrol</span>
        </h1>
        <div className="header-status">
          <span>Coordinator Heartbeat: {heartbeat?.timestamp ? heartbeat.timestamp.toFixed(2) : "--"}</span>
        </div>
      </header>

      <nav className="app-nav">
        <button
          className={`nav-btn ${activeTab === "split_optics" ? "active" : ""}`}
          onClick={() => setActiveTab("split_optics")}
        >
          Split Optics
        </button>
        <button
          className={`nav-btn ${activeTab === "laser_overhead" ? "active" : ""}`}
          onClick={() => setActiveTab("laser_overhead")}
        >
          Laser &amp; Overhead
        </button>
        <button
          className={`nav-btn ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => setActiveTab("settings")}
        >
          ⚙ Settings
        </button>
      </nav>

      {activeTab === "split_optics" && (
        <main className="main-content">
          <SplitOpticsPanel />
        </main>
      )}

      {activeTab === "laser_overhead" && (
        <main className="main-content">
          <LaserOverheadPanel />
        </main>
      )}

      {activeTab === "settings" && (
        <main className="main-content">
          <SettingsPanel />
        </main>
      )}
    </div>
  );
}
