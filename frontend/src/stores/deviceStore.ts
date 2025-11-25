import { create } from "zustand";
import { persist } from "zustand/middleware";

interface DeviceStatus {
  connected: boolean;
  enabled?: boolean;
  homed?: boolean;
  current_position?: number;
  position_mode?: string;
  error?: string;
  last_updated?: number;
}

interface DeviceStore {
  // Device statuses
  meca500Status: DeviceStatus | null;
  pdxc2Status: DeviceStatus | null;
  xyMotorStatus: DeviceStatus | null;
  botaStatus: DeviceStatus | null;

  // Update functions
  setMeca500Status: (status: DeviceStatus | null) => void;
  setPdxc2Status: (status: DeviceStatus | null) => void;
  setXyMotorStatus: (status: DeviceStatus | null) => void;
  setBotaStatus: (status: DeviceStatus | null) => void;

  // Get functions
  getMeca500Status: () => DeviceStatus | null;
  getPdxc2Status: () => DeviceStatus | null;
  getXyMotorStatus: () => DeviceStatus | null;
  getBotaStatus: () => DeviceStatus | null;
}

export const useDeviceStore = create<DeviceStore>()(
  persist(
    (set, get) => ({
      meca500Status: null,
      pdxc2Status: null,
      xyMotorStatus: null,
      botaStatus: null,

      setMeca500Status: (status) =>
        set({
          meca500Status: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),
      setPdxc2Status: (status) =>
        set({
          pdxc2Status: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),
      setXyMotorStatus: (status) =>
        set({
          xyMotorStatus: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),
      setBotaStatus: (status) =>
        set({
          botaStatus: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),

      getMeca500Status: () => get().meca500Status,
      getPdxc2Status: () => get().pdxc2Status,
      getXyMotorStatus: () => get().xyMotorStatus,
      getBotaStatus: () => get().botaStatus,
    }),
    {
      name: "device-store",
      version: 1,
      partialize: (state) => ({
        meca500Status: state.meca500Status,
        pdxc2Status: state.pdxc2Status,
        xyMotorStatus: state.xyMotorStatus,
        botaStatus: state.botaStatus,
      }),
    }
  )
);
