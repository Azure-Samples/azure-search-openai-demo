import { useEffect, useRef, useState } from "react";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { useMsal } from "@azure/msal-react";
import { EventType } from "@azure/msal-browser";
import { useLogin, checkLoggedIn } from "./authConfig";
import { LoginContext } from "./loginContext";
import Layout from "./pages/layout/Layout";

const LayoutWrapper = () => {
    const [loggedIn, setLoggedIn] = useState(false);
    if (useLogin) {
        const { instance } = useMsal();
        // Keep track of the mounted state to avoid setting state in an unmounted component
        const mounted = useRef<boolean>(true);
        useEffect(() => {
            mounted.current = true;

            const refresh = () => {
                checkLoggedIn(instance)
                    .then(isLoggedIn => {
                        if (mounted.current) setLoggedIn(isLoggedIn);
                    })
                    .catch(e => {
                        console.error("checkLoggedIn failed", e);
                    });
            };

            // Initial check on mount (may already be signed in from a prior session).
            refresh();

            // Keep loggedIn in sync with MSAL. Both LOGIN_SUCCESS/LOGOUT_SUCCESS and
            // ACTIVE_ACCOUNT_CHANGED are needed because getActiveAccount() may still
            // return null right after LOGIN_SUCCESS fires — msal-react docs recommend
            // subscribing to ACTIVE_ACCOUNT_CHANGED for this reason.
            // https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-react/docs/hooks.md#usemsal-hook
            const callbackId = instance.addEventCallback(event => {
                if (
                    event.eventType === EventType.LOGIN_SUCCESS ||
                    event.eventType === EventType.LOGOUT_SUCCESS ||
                    event.eventType === EventType.ACTIVE_ACCOUNT_CHANGED ||
                    event.eventType === EventType.ACQUIRE_TOKEN_SUCCESS
                ) {
                    refresh();
                }
            });

            return () => {
                mounted.current = false;
                if (callbackId) {
                    instance.removeEventCallback(callbackId);
                }
            };
        }, [instance]);

        return (
            <LoginContext.Provider value={{ loggedIn, setLoggedIn }}>
                <FluentProvider theme={webLightTheme} style={{ height: "100%", backgroundColor: "transparent" }}>
                    <Layout />
                </FluentProvider>
            </LoginContext.Provider>
        );
    } else {
        return (
            <LoginContext.Provider
                value={{
                    loggedIn,
                    setLoggedIn
                }}
            >
                <FluentProvider theme={webLightTheme} style={{ height: "100%", backgroundColor: "transparent" }}>
                    <Layout />
                </FluentProvider>
            </LoginContext.Provider>
        );
    }
};

export default LayoutWrapper;
