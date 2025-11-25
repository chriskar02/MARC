import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: Number(env.VITE_DEV_PORT || 5173),
      host: true,
      proxy: {
        "/api": env.VITE_BACKEND_HTTP || "http://127.0.0.1:8000",
      },
    },
    build: {
      target: "esnext",
    },
  };
});
