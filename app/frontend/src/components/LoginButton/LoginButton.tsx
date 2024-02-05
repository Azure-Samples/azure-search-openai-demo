import { DefaultButton } from "@fluentui/react";
import { useMsal } from "@azure/msal-react";

import styles from "./LoginButton.module.css";
import { getRedirectUri, loginRequest } from "../../authConfig";
import { appServicesToken, appServicesLogout } from "../../authConfig";

export const LoginButton = () => {
    const { instance } = useMsal();
    const activeAccount = instance.getActiveAccount();
    const isLoggedIn = (activeAccount || appServicesToken) != null;

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
            .catch(error => console.log(error));
    };
    const handleLogoutPopup = () => {
        if (activeAccount) {
            instance
                .logoutPopup({
                    mainWindowRedirectUri: "/", // redirects the top level app after logout
                    account: instance.getActiveAccount()
                })
                .catch(error => console.log(error));
        } else {
            appServicesLogout();
        }
    };
    const logoutText = `Logout\n${activeAccount?.username ?? appServicesToken?.user_claims?.preferred_username}`;
    return (
        <DefaultButton
            text={isLoggedIn ? logoutText : "Login"}
            className={styles.loginButton}
            onClick={isLoggedIn ? handleLogoutPopup : handleLoginPopup}
        ></DefaultButton>
    );
};
