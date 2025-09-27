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
      "/api": {
        target: "https://api.onebor.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, "/panda"),
      },
    },
  },
});

/*
  BAD VERSION: 
  server: {
      port: 8686,
      proxy: {
        "/api": {
          target: "https://api.onebor.com",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, "/panda"),
          configure: (proxy, options) => {
            proxy.on("proxyReq", (proxyReq, req, res) => {
              // Set the Origin header to make it appear as if the request is coming from app.onebor.com
              proxyReq.setHeader("Origin", "https://app.onebor.com");
              proxyReq.setHeader("Referer", "https://app.onebor.com");
            });
          },
        },
      },
    },


*/
