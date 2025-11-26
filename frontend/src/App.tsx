import { useState } from "react";
import CameraStream from "./components/camera/CameraStream";
import TelemetryPanel from "./components/plots/TelemetryPanel";
import { useChannel } from "./hooks/useChannel";
import XYMotorControl from "./components/motors/XYMotorControl";
import RobotCommandConsole from "./components/robot/RobotCommandConsole";
import BotaFeedback from "./components/sensors/BotaFeedback";
import JointManualControl from "./components/robot/JointManualControl";
import SettingsPanel from "./components/robot/SettingsPanel";
import PdxcControl from "./components/robot/PdxcControl";

export default function App() {
  const heartbeat = useChannel("telemetry/realtime");
  const [activeTab, setActiveTab] = useState<"base" | "robot" | "settings">("base");

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
          className={`nav-btn ${activeTab === "base" ? "active" : ""}`}
          onClick={() => setActiveTab("base")}
        >
          XY Base Control
        </button>
        <button
          className={`nav-btn ${activeTab === "robot" ? "active" : ""}`}
          onClick={() => setActiveTab("robot")}
        >
          Robot Control
        </button>
        <button
          className={`nav-btn ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => setActiveTab("settings")}
        >
          ⚙ Settings
        </button>
      </nav>

      {activeTab === "base" && (
        <main className="main-content">
          <div className="grid-2col">
            <XYMotorControl />
            <CameraStream workerName="basler_camera" />
          </div>
        </main>
      )}

      {activeTab === "robot" && (
        <main className="main-content">
          <div className="grid-3col">
            <section className="panel">
              <RobotCommandConsole />
            </section>
            <section className="panel">
              <BotaFeedback />
              <PdxcControl />
            </section>
            <section className="panel">
              <JointManualControl />
            </section>
          </div>
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
