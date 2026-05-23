import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy /index and /chat to FastAPI backend
      "/index": "http://localhost:8000",
      "/chat":  "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
