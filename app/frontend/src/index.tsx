import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, AccountInfo } from "@azure/msal-browser";
import { QueryClient, QueryClientProvider } from "react-query";

import "./index.css";
import { msalConfig, useLogin } from "./authConfig";
import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";

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
                element: <Chat />
            },
            {
                path: "qa",
                lazy: () => import("./pages/ask/Ask")
            },
            {
                path: "eval",
                lazy: () => import("./pages/eval/Eval")
            },
            {
                path: "eval_cases",
                lazy: () => import("./pages/eval/EvalFeedback")
            },
            {
                path: "eval_batch",
                lazy: () => import("./pages/eval/EvalBatch")
            },
            {
                path: "*",
                lazy: () => import("./pages/NoPage")
            }
        ]
    }
]);

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
    </QueryClientProvider>
);
