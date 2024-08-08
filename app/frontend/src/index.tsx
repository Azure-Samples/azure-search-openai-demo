import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { FluentProvider, webLightTheme, Theme } from "@fluentui/react-components";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, AccountInfo } from "@azure/msal-browser";
import { msalConfig, useLogin } from "./authConfig";

import "./index.css";

import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";
import Manage from "./pages/manage/Manage";
import Login from "./pages/login/Login";



// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth, onAuthStateChanged } from 'firebase/auth';
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBpc-yWt3kwpXy7oy2XKzC2p-fRNrOcagQ",
  authDomain: "projectpalai-83a5f.firebaseapp.com",
  projectId: "projectpalai-83a5f",
  storageBucket: "projectpalai-83a5f.appspot.com",
  messagingSenderId: "430310511920",
  appId: "1:430310511920:web:cb0e58341ef191e799a4f5",
  measurementId: "G-TVX8H2KFTD"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export {auth}






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
                lazy: () => import("./pages/oneshot/OneShot")
            },
            {
                path: "/manage",
                element: <Manage />
            },
            {
                path: "/login",
                element: <Login />
            },
            {
                path: "*",
                lazy: () => import("./pages/NoPage")
            }
        ]
    }
]);

const customTheme: Theme = {
    ...webLightTheme,
    colorNeutralBackground1: " #f2f2f2;"
};
ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <FluentProvider theme={customTheme}>
            <RouterProvider router={router} />
        </FluentProvider>
    </React.StrictMode>
);
