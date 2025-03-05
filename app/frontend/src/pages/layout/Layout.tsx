import { Outlet, Link, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useMsal } from "@azure/msal-react";
import { EventType } from "@azure/msal-browser"; // ✅ Import correct event type
import styles from "./Layout.module.css";
import { LoginButton } from "../../components/LoginButton";
import { SplashScreen } from "../../components/SplashScreen";
import { Info24Regular } from "@fluentui/react-icons"; // Fluent UI info icon
import { appServicesToken, appServicesLogout } from "../../authConfig";

const Layout = () => {
    const { instance, accounts } = useMsal();
    const navigate = useNavigate();
    const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);

    useEffect(() => {
        const checkAuthStatus = () => {
            const activeAccount = instance.getActiveAccount();
            if (activeAccount || appServicesToken) {
                setIsLoggedIn(true);
            } else {
                setIsLoggedIn(false);
            }
        };

        checkAuthStatus();
        
        // ✅ Use MSAL event listener to detect login state change
        const accountListener = instance.addEventCallback((event) => {
            if (event.eventType === EventType.LOGIN_SUCCESS) {
                setIsLoggedIn(true);
                navigate("/", { replace: true }); // ✅ Navigate only after login
            } else if (event.eventType === EventType.LOGOUT_SUCCESS) {
                setIsLoggedIn(false);
                navigate("/"); // ✅ Go back to splash screen on logout
            }
        });

        return () => {
            if (accountListener) {
                instance.removeEventCallback(accountListener);
            }
        };
    }, [instance, accounts, navigate]);

    const handleLogout = () => {
        const activeAccount = instance.getActiveAccount();
        if (activeAccount) {
            instance.logoutPopup({
                mainWindowRedirectUri: "/", // Redirects app after logout
                account: activeAccount,
            });
        } else {
            appServicesLogout();
        }
        setIsLoggedIn(false);
        navigate("/"); // ✅ Ensure user is redirected to login after logout
    };

    if (isLoggedIn === null) {
        return <SplashScreen />; // ✅ Shows splash screen initially
    }

    return isLoggedIn ? (
        <div className={styles.layout}>
            {/* Sidebar */}
            <aside className={styles.sidebar}>
                <div className={styles.sidebarContent}>
                    <Link to="/" className={styles.logoContainer}>
                        <img
                            src="https://staudiolydevaueast001.blob.core.windows.net/images-blob/pow_whiddon.svg"
                            alt="Whiddon logo"
                            className={styles.logo}
                        />
                    </Link>
                </div>
            </aside>

            {/* Main Content */}
            <div className={styles.mainContent}>
                {/* Header */}
                <header className={styles.header} role="banner">
                    <h2 className={styles.headerTitle}>Assistant.AI</h2>
                    <div className={styles.logoutContainer}>
                        <Info24Regular className={styles.infoIcon} title="More Info" />
                        <button onClick={handleLogout} className={styles.logoutButton}>Logout</button>
                    </div>
                </header>

                {/* Page Content */}
                <main className={styles.pageContent}>
                    <Outlet />
                </main>
            </div>
        </div>
    ) : (
        <SplashScreen />
    );
};

export default Layout;
