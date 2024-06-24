import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, AccountInfo } from "@azure/msal-browser";
import { msalConfig, useLogin } from "./authConfig";

import "./index.css";

import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";

import Search from "./pages/search/SearchTab";

var layout;
if (useLogin) {
    var msalInstance = new PublicClientApplication(msalConfig);

    // Default to using the first account if no account is active on page load
    if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length > 0) {
        // Account selection logic is app dependent. Adjust as needed for different use cases.
        msalInstance.setActiveAccount(msalInstance.getActiveAccount());
    }

    // Listen for sign-in event and set active account
    msalInstance.addEventCallback(event => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
            const account = event.payload as AccountInfo;
            msalInstance.setActiveAccount(account);
        }
    });

    layout = (
        <MsalProvider instance={msalInstance}>
            <Layout />
        </MsalProvider>
    );
} else {
    layout = <Layout />;
}

initializeIcons();

const SearchTab = React.lazy(() => import("./pages/search/SearchTab").then(module => ({ default: module.default })));

const router = createHashRouter([
    {
        path: "/",
        element: layout,
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
                path: "search",
                element: <React.Suspense fallback={<div>Loading...</div>}>
                   <SearchTab />
                 </React.Suspense>
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
        <RouterProvider router={router} />
    </React.StrictMode>
);
