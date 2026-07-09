/// <reference types="node" />
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Vite serves redirect.html at "/redirect.html", but the MSAL redirect URI is "/redirect"
// (matching the deployed backend route). This tiny middleware rewrites "/redirect" to
// "/redirect.html" during dev so the popup handshake works locally.
const redirectAlias: Plugin = {
    name: "redirect-html-alias",
    configureServer(server) {
        server.middlewares.use((req, _res, next) => {
            if (req.url === "/redirect" || req.url?.startsWith("/redirect?")) {
                req.url = "/redirect.html" + req.url.slice("/redirect".length);
            }
            next();
        });
    }
};

// https://vitejs.dev/config/
export default defineConfig(() => {
    const backendPort = process.env.BACKEND_PORT || "50505";
    const backendUrl = `http://localhost:${backendPort}`;
    return {
        plugins: [react(), redirectAlias],
        resolve: {
            preserveSymlinks: true
        },
        build: {
            outDir: "../backend/static",
            emptyOutDir: true,
            sourcemap: true,
            rollupOptions: {
                input: {
                    main: resolve(__dirname, "index.html"),
                    // Dedicated MSAL popup-redirect page — contains only the bridge script.
                    // See https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/login-user.md#redirecturi-considerations
                    redirect: resolve(__dirname, "redirect.html")
                },
                output: {
                    manualChunks: id => {
                        // Keep the MSAL redirect-bridge chunk isolated so that the
                        // dedicated redirect.html popup entry does not pull in React,
                        // Fluent UI, or the rest of the SPA vendor bundle.
                        if (id.includes("@azure/msal-browser") || id.includes("@azure/msal-common")) {
                            return "msal";
                        }
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
