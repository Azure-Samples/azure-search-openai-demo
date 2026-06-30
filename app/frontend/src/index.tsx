import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { I18nextProvider } from "react-i18next";
import { HelmetProvider } from "react-helmet-async";
import { initializeIcons } from "@fluentui/font-icons-mdl2"; // ✅ эндээс
import { MsalProvider } from "@azure/msal-react";
import { AuthenticationResult, EventType, PublicClientApplication } from "@azure/msal-browser";
import "@fluentui/react/dist/css/fabric.css";
import "./index.css";

import Chat from "./pages/chat/Chat";
import LayoutWrapper from "./layoutWrapper";
import i18next from "./i18n/config";
import { msalConfig, useLogin } from "./authConfig";

initializeIcons(); // ✅ ганц удаа

const router = createHashRouter([
    {
        path: "/",
        element: <LayoutWrapper />,
        children: [
            { index: true, element: <Chat /> },
            { path: "qa", lazy: () => import("./pages/ask/Ask") },
            { path: "*", lazy: () => import("./pages/NoPage") }
        ]
    }
]);

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);

(async () => {
    let msalInstance: PublicClientApplication | undefined;

    if (useLogin) {
        msalInstance = new PublicClientApplication(msalConfig);
        try {
            await msalInstance.initialize();

            if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length > 0) {
                msalInstance.setActiveAccount(msalInstance.getAllAccounts()[0]);
            }

            msalInstance.addEventCallback(event => {
                if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
                    const result = event.payload as AuthenticationResult;
                    if (result.account) {
                        msalInstance!.setActiveAccount(result.account);
                    }
                }
            });
        } catch (e) {
            console.error("MSAL initialize failed", e);
            msalInstance = undefined;
        }
    }

    const appTree = (
        <React.StrictMode>
            <I18nextProvider i18n={i18next}>
                <HelmetProvider>
                    {useLogin && msalInstance ? (
                        <MsalProvider instance={msalInstance}>
                            <RouterProvider router={router} />
                        </MsalProvider>
                    ) : (
                        <RouterProvider router={router} />
                    )}
                </HelmetProvider>
            </I18nextProvider>
        </React.StrictMode>
    );

    root.render(appTree);
})();
