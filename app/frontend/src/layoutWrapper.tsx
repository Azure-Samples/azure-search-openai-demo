import { AuthenticationResult, EventType, PublicClientApplication } from "@azure/msal-browser";
import { checkLoggedIn, msalConfig, useLogin } from "./authConfig";
import { useEffect, useMemo, useRef, useState } from "react";
import { MsalProvider } from "@azure/msal-react";
import { LoginContext } from "./loginContext";
import Layout from "./pages/layout/Layout";

const LayoutWrapper = () => {
    const [loggedIn, setLoggedIn] = useState(false);
    if (useLogin) {
        // Create a stable MSAL instance (avoid re-init/duplicate listeners; single shared client for MsalProvider).
        const msalInstance = useMemo(() => new PublicClientApplication(msalConfig), []);
        const [initialized, setInitialized] = useState(false);
        // Track mount state so we don't call setState after unmount if async init resolves late
        const mounted = useRef<boolean>(true);

        useEffect(() => {
            // React StrictMode in development invokes effects twice (mount -> cleanup -> mount).
            // Reset the flag here so this run is considered mounted.
            mounted.current = true;
            const init = async () => {
                try {
                    await msalInstance.initialize();

                    // Default to using the first account if no account is active on page load
                    if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length > 0) {
                        msalInstance.setActiveAccount(msalInstance.getAllAccounts()[0]);
                    }

                    // Listen for sign-in event and set active account
                    msalInstance.addEventCallback(event => {
                        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
                            const result = event.payload as AuthenticationResult;
                            if (result.account) {
                                msalInstance.setActiveAccount(result.account);
                            }
                        }
                    });

                    if (mounted.current) {
                        try {
                            const isLoggedIn = await checkLoggedIn(msalInstance);
                            setLoggedIn(isLoggedIn);
                        } catch (e) {
                            // Swallow check error but still allow app to render
                            console.error("checkLoggedIn failed", e);
                        }
                    }
                } catch (e) {
                    console.error("MSAL initialize failed", e);
                } finally {
                    if (mounted.current) {
                        setInitialized(true);
                    }
                }
            };
            init();
            return () => {
                // On unmount: flag as unmounted so any pending async in init() doesn't call setState
                // This avoids React warnings about setting state on an unmounted component.
                mounted.current = false;
            };
        }, [msalInstance]);

        if (!initialized) {
            // Lightweight placeholder while MSAL initializes
            return <p>Loading authentication…</p>;
        }

        return (
            <MsalProvider instance={msalInstance}>
                <LoginContext.Provider value={{ loggedIn, setLoggedIn }}>
                    <Layout />
                </LoginContext.Provider>
            </MsalProvider>
        );
    } else {
        return (
            <LoginContext.Provider
                value={{
                    loggedIn,
                    setLoggedIn
                }}
            >
                <Layout />
            </LoginContext.Provider>
        );
    }
};

export default LayoutWrapper;
