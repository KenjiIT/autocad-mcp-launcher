import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// Bản LOCAL: không đăng nhập, không có launcher nối ra từ máy khác. Vite chỉ chuyển tiếp /api sang gateway cục bộ.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, resolve(__dirname, "../gateway"), "");
  return {
    plugins: [react()],
    server: {
      port: 5174,
      allowedHosts: [".trycloudflare.com"],
      proxy: {
        "/api": { target: process.env.GATEWAY_URL ?? `http://127.0.0.1:${env.PORT ?? 8788}` },
      },
    },
  };
});
