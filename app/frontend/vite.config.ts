import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        outDir: "../backend/static",
        emptyOutDir: true,
        sourcemap: true
    },
    server: {
        proxy: {
            "/ask": {
                target: "http://127.0.0.1:5000",
                changeOrigin: true,
                secure: false
            },
            "/chat": {
                target: "http://127.0.0.1:5000",
                changeOrigin: true,
                secure: false
            },
            "/conversation": {
                target: "http://127.0.0.1:5000",
                changeOrigin: true,
                secure: false
            }
        }
    }
});
