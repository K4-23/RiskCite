import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发时 /api 代理到本地 FastAPI；构建产物输出到 dist/，由 FastAPI 托管
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
