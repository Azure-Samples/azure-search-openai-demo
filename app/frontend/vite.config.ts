import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],

    resolve: {
        preserveSymlinks: false,
        dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime"]
    },

    optimizeDeps: {
        include: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime"]
    },

    build: {
        outDir: "../backend/static",
        emptyOutDir: true,
        sourcemap: true,
        target: "esnext"
    },

    server: {
        proxy: {
            "/content/": "http://localhost:50505",
            "/auth_setup": "http://localhost:50505",
            "/.auth/me": "http://localhost:50505",
            "/ask": "http://localhost:50505",
            "/chat": "http://localhost:50505",
            "/speech": "http://localhost:50505",
            "/config": "http://localhost:50505",
            "/upload": "http://localhost:50505",
            "/delete_uploaded": "http://localhost:50505",
            "/list_uploaded": "http://localhost:50505",
            "/chat_history": "http://localhost:50505"
        }
    }
});
