import { Outlet, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { useMsal } from "@azure/msal-react";
import styles from "./Layout.module.css";
import { LoginButton } from "../../components/LoginButton";
import { DefaultButton } from "@fluentui/react";
import { Info24Regular } from "@fluentui/react-icons"; // Fluent UI info icon
import { appServicesToken, appServicesLogout } from "../../authConfig";
import { SplashScreen } from "../../components/SplashScreen";

const Layout = () => {
     const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => {
        return localStorage.getItem("isLoggedIn") === "true";
    });

    useEffect(() => {
        localStorage.setItem("isLoggedIn", isLoggedIn.toString());
    }, [isLoggedIn]); // Update storage when login state changes

    const handleLogin = () => {
        setIsLoggedIn(true);
    };

    const handleLogout = () => {
        setIsLoggedIn(false);
        localStorage.removeItem("isLoggedIn"); // Clear stored state on logout
    };

    return (
        isLoggedIn ? (
            <div className={styles.layout}>
                <aside className={styles.sidebar}>
                    <div className={styles.sidebarContent}>
                        {/* <a href="#" style={{ textDecoration: "none" }}>
                            <p className={styles.poweredBy}>Powered by</p>
                        </a> */}
                        <Link to="/" className={styles.logoContainer}>
                            <img
                                src="https://staudiolydevaueast001.blob.core.windows.net/images-blob/pow_whiddon.svg"
                               // src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQCUBECfpk4SqfCAkBtYz5LpMD9AVXcTMtGiA&s"
                                alt="Whiddon logo"
                                className={styles.logo}
                            />
                        </Link>
                    </div>
                </aside>
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
            <SplashScreen onLogin={handleLogin} />
        )
    );
};

export default Layout;
