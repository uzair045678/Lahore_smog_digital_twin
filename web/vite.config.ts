import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  publicDir: "public",
  build: {
    target: "es2022",
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        lowPilot: resolve(__dirname, "low-pilot.html"),
        highPilot: resolve(__dirname, "high-pilot.html"),
      },
    },
  },
});
