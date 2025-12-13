/// <reference types="vite/client" />

import type { Buffer } from "buffer";

// Extend Window interface to include Buffer polyfill
declare global {
    interface Window {
        Buffer: typeof Buffer;
    }
}

export {};