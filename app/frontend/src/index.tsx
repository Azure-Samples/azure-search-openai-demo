import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, AccountInfo } from "@azure/msal-browser";
import { msalConfig, useLogin } from "./authConfig";

import "./index.css";

import Layout from "./pages/layout/Layout";
import { ThemeProvider } from "./context/ThemeContext";

// Lazy load the components
const Chat = React.lazy(() => import("./pages/chat/Chat"));
const Sources = React.lazy(() => import("./pages/sources/Sources"));
const Ask = React.lazy(() => import("./pages/ask/Ask"));
const NoPage = React.lazy(() => import("./pages/NoPage"));

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

const router = createHashRouter([
    {
        path: "/",
        element: layout,
        children: [
            {
                index: true,
                element: (
                    <React.Suspense fallback={<div>Loading...</div>}>
                        <Chat />
                    </React.Suspense>
                )
            },
            {
                path: "sources/*", // Add '/*' to allow nested routes
                element: (
                    <React.Suspense fallback={<div>Loading...</div>}>
                        <Sources />
                    </React.Suspense>
                )
            },
            {
                path: "qa",
                element: (
                    <React.Suspense fallback={<div>Loading...</div>}>
                        <Ask />
                    </React.Suspense>
                )
            },
            {
                path: "*",
                element: (
                    <React.Suspense fallback={<div>Loading...</div>}>
                        <NoPage />
                    </React.Suspense>
                )
            }
        ]

        // children: [
        //     {
        //         index: true,
        //         element: <Chat />
        //     },
        //     {
        //         path: "sources",
        //         lazy: () => import("./pages/sources/Sources")
        //     },
        //     {
        //         path: "qa",
        //         lazy: () => import("./pages/ask/Ask")
        //     },
        //     {
        //         path: "*",
        //         lazy: () => import("./pages/NoPage")
        //     }
        // ]
    }
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <ThemeProvider>
            <RouterProvider router={router} />
        </ThemeProvider>
    </React.StrictMode>
);
