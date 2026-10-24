import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  publicDir: "public",
  build: {
    target: "es2022",
  },
});