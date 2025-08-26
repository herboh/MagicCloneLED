import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // Allow external connections
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
  // Resolve path aliases if needed
  resolve: {
    alias: {
      "@": "/src",
    },
  },
});

