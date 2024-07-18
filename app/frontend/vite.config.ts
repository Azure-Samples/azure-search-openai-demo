import { defineConfig } from "vite";
import commonConfig from "./vite.config.ts";

export default defineConfig({
    ...commonConfig,
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
            "/list_uploaded": "http://localhost:50505"
        }
    }
});
