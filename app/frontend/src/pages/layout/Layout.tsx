import { Outlet, NavLink, Link } from "react-router-dom";

import dna_logo from "../../assets/powered_dna_blanco.png";

import styles from "./Layout.module.css";

const Layout = () => {
    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <h3 className={styles.headerTitle}>Grupo Bimbo ChatGPT | Demo</h3>
                    </Link>
                    <nav>
                        <ul className={styles.headerNavList}>
                            <li>
                                <NavLink to="/" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                    Chat
                                </NavLink>
                            </li>
                            <li className={styles.headerNavLeftMargin}>
                                <NavLink to="/qa" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                    Ask a question
                                </NavLink>
                            </li>        
                        </ul>
                    </nav>
                    <li className={styles.headerNavLeftMargin}>
                                <a href="https://apps.powerapps.com/play/e/9747ef38-2157-4070-a717-06c06a45c8e3/a/5da93623-b160-450e-aea9-57b217b56763?tenantId=973ba820-4a58-4246-84bf-170e50b3152a&source=AppSharedV3&hint=326f04c7-3009-48e7-bae4-bfb3c5e24684
" 
title="Link to DnA AI Apps">
                                    <img
                                        src={dna_logo}
                                        alt="DnAlogo"
                                        aria-label="Link to DnA AI Apps"
                                        height="400px"
                                        className={styles.githubLogo}
                                    />
                                </a>
                            </li>
                    <h4 className={styles.headerRightText}>DEV Version</h4>
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Layout;
