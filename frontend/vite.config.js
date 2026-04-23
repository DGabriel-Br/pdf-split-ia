import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/upload": "http://localhost:8000",
      "/jobs": "http://localhost:8000",
      "/corrections": "http://localhost:8000",
    },
  },
});
