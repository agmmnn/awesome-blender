import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { nitro } from "nitro/vite";

export default defineConfig({
  server: {
    port: 3000,
  },
  resolve: {
    tsconfigPaths: true,
  },
  build: {
    chunkSizeWarningLimit: 1000,
  },
  plugins: [
    tailwindcss(),
    tanstackStart(),
    nitro({
      preset: process.env.VERCEL ? "vercel" : undefined,
    }),
    viteReact(),
  ],
});
