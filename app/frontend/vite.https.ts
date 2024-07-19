import fs from "fs";

import { defineConfig } from "vite";

import commonConfig from "./vite.common.ts";

export default defineConfig({
    ...commonConfig,
    server: {
        proxy: {
            "/content/": "https://localhost:50505",
            "/auth_setup": "https://localhost:50505",
            "/.auth/me": "https://localhost:50505",
            "/ask": "https://localhost:50505",
            "/chat": "https://localhost:50505",
            "/speech": "https://localhost:50505",
            "/config": "https://localhost:50505",
            "/upload": "https://localhost:50505",
            "/delete_uploaded": "https://localhost:50505",
            "/list_uploaded": "https://localhost:50505"
        },
        https: {
            cert: fs.readFileSync("../../localcert.pem"),
            key: fs.readFileSync("../../localcert_key.pem")
        }
    }
});
