import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy /api calls to the FastAPI backend on :8000 so the SPA and API
// look same-origin to the browser. In production FastAPI serves the built SPA.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
