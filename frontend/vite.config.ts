import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API (Django, port 8050) is proxied so the browser sees a single origin
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8050",
      "/media": "http://127.0.0.1:8050",
    },
  },
});
