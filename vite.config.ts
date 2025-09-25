import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API Configuration - IMPORTANT: Only valid API URL is https://api.onebor.com/panda
const API_BASE_URL = "https://api.onebor.com/panda";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    global: "globalThis",
  },
  server: {
    proxy: {
      "/api": {
        target: API_BASE_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
