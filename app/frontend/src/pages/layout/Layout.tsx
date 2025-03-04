import { Outlet, Link } from "react-router-dom";
import github from "../../assets/github.svg";
import styles from "./Layout.module.css";
import { useLogin } from "../../authConfig";
import { LoginButton } from "../../components/LoginButton";
import { Info24Regular } from "@fluentui/react-icons"; // Fluent UI info icon

const Layout = () => {
    return (
        <div className={styles.layout}>
            {/* Sidebar */}
            <aside className={styles.sidebar}>
                <div className={styles.sidebarContent}>
                    <a href="#" style={{ textDecoration: "none" }}>
                        <p className={styles.poweredBy}>Powered by</p>
                    </a>
                    <Link to="/" className={styles.logoContainer}>
                        <img
                            src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQCUBECfpk4SqfCAkBtYz5LpMD9AVXcTMtGiA&s"
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
                    <Info24Regular className={styles.infoIcon} title="More Info" />
                </header>

                {/* Page Content */}
                <main className={styles.pageContent}>{useLogin ? <LoginButton /> : <Outlet />}</main>
            </div>
        </div>
    );
};

export default Layout;
