import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, AccountInfo } from "@azure/msal-browser";
import { msalConfig } from "./authConfig"; // Remove useLogin here

import "./index.css";
import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";

// ✅ Always create MSAL instance
const msalInstance = new PublicClientApplication(msalConfig);

// ✅ Select the first available account if no active account exists
const accounts = msalInstance.getAllAccounts();
if (!msalInstance.getActiveAccount() && accounts.length > 0) {
    msalInstance.setActiveAccount(accounts[0]);
}

// ✅ Listen for sign-in events and set active account
msalInstance.addEventCallback(event => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
        const account = event.payload as AccountInfo;
        msalInstance.setActiveAccount(account);
    }
});

// ✅ Wrap the entire app in MsalProvider
initializeIcons();

const router = createHashRouter([
    {
        path: "/",
        element: <Layout />, // Layout will handle authentication logic
        children: [
            {
                index: true,
                element: <Chat />
            },
            {
                path: "qa",
                lazy: () => import("./pages/ask/Ask")
            },
            {
                path: "*",
                lazy: () => import("./pages/NoPage")
            }
        ]
    }
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <MsalProvider instance={msalInstance}>
            <RouterProvider router={router} />
        </MsalProvider>
    </React.StrictMode>
);
