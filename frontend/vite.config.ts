import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In local dev, Vite serves the React app on :5173 and forwards /api calls to
// FastAPI on :8000. In production FastAPI serves the built files itself.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
