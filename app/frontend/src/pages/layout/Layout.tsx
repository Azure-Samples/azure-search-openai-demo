import { Outlet, Link } from "react-router-dom";

import logo from "../../assets/logo.svg";

import styles from "./Layout.module.css";

const Layout = () => {
    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <img src={logo} alt="Bupa logo" aria-label="Link to bupa" height="20px" className={styles.githubLogo} />
                    </Link>
                </div>
            </header>
            <Outlet />
        </div>
    );
};

export default Layout;
