import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

var useDotnet = process.env.AZURE_SEARCH_OPENAI_USE_DOTNET == "true" ? true : false;
var deployPath = useDotnet ? "../backend-dotnet/wwwroot" : "../backend/static";
console.log(`deploy build to ${deployPath}`);

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        outDir: deployPath,
        emptyOutDir: true,
        sourcemap: true
    },
    server: {
        proxy: {
            "/ask": "http://localhost:5000",
            "/chat": "http://localhost:5000"
        }
    }
});
