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
  meca500Status: DeviceStatus | null;
  standaStatus: DeviceStatus | null;
  botaStatus: DeviceStatus | null;

  setMeca500Status: (status: DeviceStatus | null) => void;
  setStandaStatus: (status: DeviceStatus | null) => void;
  setBotaStatus: (status: DeviceStatus | null) => void;
}

export const useDeviceStore = create<DeviceStore>()(
  persist(
    (set) => ({
      meca500Status: null,
      standaStatus: null,
      botaStatus: null,

      setMeca500Status: (status) =>
        set({
          meca500Status: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),
      setStandaStatus: (status) =>
        set({
          standaStatus: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),
      setBotaStatus: (status) =>
        set({
          botaStatus: status
            ? { ...status, last_updated: Date.now() }
            : null,
        }),
    }),
    {
      name: "device-store",
      version: 2,
      partialize: (state) => ({
        meca500Status: state.meca500Status,
        standaStatus: state.standaStatus,
        botaStatus: state.botaStatus,
      }),
    }
  )
);
