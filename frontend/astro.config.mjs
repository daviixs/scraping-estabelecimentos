import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import tailwind from "@astrojs/tailwind";

export default defineConfig({
  srcDir: "src",
  outDir: "../frontend/dist",
  integrations: [react(), tailwind()],
  build: {
    format: "file",
  },
  server: {
    host: "127.0.0.1",
    port: 4321,
  },
});
