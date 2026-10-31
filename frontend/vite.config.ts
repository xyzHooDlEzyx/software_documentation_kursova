import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api/v1": {
        target: "http://localhost:8000",
        // Keep the browser Origin and forwarded Host aligned for Django CSRF.
        changeOrigin: false,
      },
    },
  },
});
