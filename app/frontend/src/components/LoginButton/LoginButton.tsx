import { DefaultButton } from "@fluentui/react";
import { useMsal } from "@azure/msal-react";

import styles from "./LoginButton.module.css";
import { getRedirectUri, loginRequest } from "../../authConfig";

export const LoginButton = () => {
    const { instance } = useMsal();
    const activeAccount = instance.getActiveAccount();
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
        instance
            .logoutPopup({
                mainWindowRedirectUri: "/", // redirects the top level app after logout
                account: instance.getActiveAccount()
            })
            .catch(error => console.log(error));
    };
    const logoutText = `Logout\n${activeAccount?.username}`;
    return (
        <DefaultButton
            text={activeAccount ? logoutText : "Login"}
            className={styles.loginButton}
            onClick={activeAccount ? handleLogoutPopup : handleLoginPopup}
        ></DefaultButton>
    );
};
