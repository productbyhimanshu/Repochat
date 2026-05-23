import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],

    // Dev server (used by `yarn dev`). Production preview ignores HMR entirely.
    server: {
      host: "0.0.0.0",
      port: 3000,
      strictPort: true,
      // Disable HMR over the K8s ingress proxy — WebSocket forwarding can be
      // flaky and Vite's reconnect-on-disconnect causes user-visible reload
      // attempts. Hot reload is reserved for local `yarn dev` runs.
      hmr: false,
      allowedHosts: true,
    },

    // Production preview server (used by supervisor via `yarn start`).
    preview: {
      host: "0.0.0.0",
      port: 3000,
      strictPort: true,
      allowedHosts: true,
    },

    define: {
      "process.env.REACT_APP_BACKEND_URL": JSON.stringify(env.REACT_APP_BACKEND_URL || ""),
    },

    build: {
      outDir: "dist",
      sourcemap: false,
      // Avoid huge single chunks
      chunkSizeWarningLimit: 1200,
    },
  };
});
