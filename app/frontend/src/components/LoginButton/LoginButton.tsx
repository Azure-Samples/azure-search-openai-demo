import { Button } from "@fluentui/react-components";
import { useMsal } from "@azure/msal-react";
import { useTranslation } from "react-i18next";

import styles from "./LoginButton.module.css";
import { getRedirectUri, loginRequest, appServicesLogout, getActiveOrFirstAccount, getUsername, checkLoggedIn } from "../../authConfig";
import { useState, useEffect, useContext } from "react";
import { LoginContext } from "../../loginContext";

export const LoginButton = () => {
    const { instance } = useMsal();
    const { loggedIn, setLoggedIn } = useContext(LoginContext);
    const [username, setUsername] = useState("");
    const { t } = useTranslation();

    // Re-fetch the username whenever loggedIn flips (LayoutWrapper drives loggedIn from MSAL events),
    // so the button correctly shows the signed-in user after a popup login/logout without a page reload.
    useEffect(() => {
        const fetchUsername = async () => {
            setUsername((await getUsername(instance)) ?? "");
        };

        fetchUsername();
    }, [instance, loggedIn]);

    const handleLoginPopup = () => {
        /**
         * When using popup and silent APIs, we recommend setting the redirectUri to a blank page or a page
         * that does not implement MSAL. Keep in mind that all redirect routes must be registered with the application
         * For more information, please follow this link: https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/login-user.md#redirecturi-considerations
         */
        instance
            .loginPopup({
                ...loginRequest,
                redirectUri: getRedirectUri()
            })
            .catch(error => console.log(error))
            .then(async () => {
                setLoggedIn(await checkLoggedIn(instance));
                setUsername((await getUsername(instance)) ?? "");
            });
    };
    const handleLogoutPopup = () => {
        // Fall back to the first cached account if there is no active account, so we always take
        // the MSAL logoutPopup path instead of accidentally triggering appServicesLogout() and
        // navigating the top window to /.auth/logout.
        const account = getActiveOrFirstAccount(instance);
        if (account) {
            instance
                .logoutPopup({
                    mainWindowRedirectUri: "/", // redirects the top level app after logout
                    account
                })
                .catch(error => console.log(error))
                .then(async () => {
                    setLoggedIn(await checkLoggedIn(instance));
                    setUsername((await getUsername(instance)) ?? "");
                });
        } else {
            appServicesLogout();
        }
    };
    return (
        <Button className={styles.loginButton} onClick={loggedIn ? handleLogoutPopup : handleLoginPopup}>
            {loggedIn ? `${t("logout")}\n${username}` : `${t("login")}`}
        </Button>
    );
};
