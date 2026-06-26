/// <reference types="node" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(() => {
    const backendPort = process.env.BACKEND_PORT || "50505";
    const backendUrl = `http://localhost:${backendPort}`;
    return {
        plugins: [react()],
        resolve: {
            preserveSymlinks: true
        },
        build: {
            outDir: "../backend/static",
            emptyOutDir: true,
            sourcemap: true,
            rollupOptions: {
                output: {
                    manualChunks: id => {
                        if (id.includes("@fluentui/react-icons")) {
                            return "fluentui-icons";
                        } else if (id.includes("@fluentui/react")) {
                            return "fluentui-react";
                        } else if (id.includes("node_modules")) {
                            return "vendor";
                        }
                    }
                }
            },
            target: "esnext"
        },
        server: {
            proxy: {
                "/content/": backendUrl,
                "/auth_setup": backendUrl,
                "/.auth/me": backendUrl,
                "/chat": backendUrl,
                "/speech": backendUrl,
                "/config": backendUrl,
                "/upload": backendUrl,
                "/delete_uploaded": backendUrl,
                "/list_uploaded": backendUrl,
                "/chat_history": backendUrl
            }
        }
    };
});
