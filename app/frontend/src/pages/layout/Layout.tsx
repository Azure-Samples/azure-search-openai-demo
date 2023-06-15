import { Outlet, NavLink, Link } from "react-router-dom";

import github from "../../assets/github.svg";

import styles from "./Layout.module.css";
import { useEffect } from "react";

const Layout = () => {
    return (
        
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                <li className={styles.headerNavLeftMargin}>
                            <a href="https://innadvisory.com/index.html" target={"_blank"} title="Innadvisory link">
                                <img
                                    src="https://innadvisory.com/uploads/3/4/7/5/34758765/logo.png"
                                    alt="Innadvisory logo"
                                    aria-label="Link to Innadvisory home page"
                                    width="240px"
                                    height="60px"
                                    className={styles.innadvisorylogo}
                                />
                            </a>
                        </li>
                    <Link to="/" className={styles.headerTitleContainer}>
                    </Link>
                    <nav>
                        <ul className={styles.headerNavList}>
                            <li>
                                <NavLink to="/" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                </NavLink>
                            </li>
                            <li className={styles.headerNavLeftMargin}>
                                
                            </li>
                            <li className={styles.headerNavLeftMargin}>
                                <a href="https://aka.ms/entgptsearch" target={"_blank"} title="Github repository link">
                                    <img
                                        src={github}
                                        alt="Github logo"
                                        aria-label="Link to github repository"
                                        width="20px"
                                        height="20px"
                                        className={styles.githubLogo}
                                    />
                                </a>
                            </li>
                        </ul>
                    </nav>
                    <h4 className={styles.headerRightText}>Azure OpenAI + created by Inn</h4>
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Layout;
