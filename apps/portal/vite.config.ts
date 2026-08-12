import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `vite dev` runs on the host, outside the Compose network, so these mirror
// nginx.conf's routes but target host ports rather than container DNS names.
// /api and /tiles stay reachable this way (api/seaweedfs keep host ports).
// The other five (terria/stac/tiler/cube/auth) point at ports docker-compose
// no longer publishes by default — add a temporary `ports:` entry for the
// service you're actively developing against, or just use the Dockerized
// portal at :8080 which reaches everything through the Compose network.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8080,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/tiles": {
        target: "http://localhost:8333",
        rewrite: (path) => path.replace(/^\/tiles/, ""),
      },
      "/terria": {
        target: "http://localhost:3001",
        rewrite: (path) => path.replace(/^\/terria/, ""),
      },
      "/stac": {
        target: "http://localhost:8081",
        rewrite: (path) => path.replace(/^\/stac/, ""),
      },
      "/tiler": {
        target: "http://localhost:8082",
        rewrite: (path) => path.replace(/^\/tiler/, ""),
      },
      "/cube": {
        target: "http://localhost:4000",
        rewrite: (path) => path.replace(/^\/cube/, ""),
      },
      "/dagster": {
        target: "http://localhost:3000",
        rewrite: (path) => path.replace(/^\/dagster/, ""),
      },
      "/auth": {
        target: "http://localhost:8083",
        rewrite: (path) => path.replace(/^\/auth/, ""),
      },
    },
  },
});
