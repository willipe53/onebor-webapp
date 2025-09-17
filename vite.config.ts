import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    global: "globalThis",
  },
  server: {
    proxy: {
      '/api': {
        target: 'https://api.onebor.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/panda'),
      },
    },
  },
});
