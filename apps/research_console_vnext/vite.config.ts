import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("./index.html", import.meta.url)),
        atlasFeasibility: fileURLToPath(new URL("./atlas-feasibility.html", import.meta.url)),
        atlasWorkbench: fileURLToPath(new URL("./atlas-workbench.html", import.meta.url)),
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
  preview: { host: "127.0.0.1", port: 4173, strictPort: true },
});
