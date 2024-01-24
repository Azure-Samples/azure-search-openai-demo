import { Outlet, NavLink, Link } from "react-router-dom";

import github from "../../assets/github.svg";
import veraqor from "../../assets/veraqor.png";
import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";

import { LoginButton } from "../../components/LoginButton";

const Layout = () => {
    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        {/* <h3 className={styles.headerTitle}>Veraqor GPT + Enterprise data | Demo</h3> */}
                        <img
                            src={veraqor}
                            alt="Veraqor logo"
                            aria-label="Link to github repository"
                            width="160px"
                            height="60px"
                            className={styles.githubLogo}
                        />
                        <h3 className={styles.headerTitle}>GPT + Enterprise data | Demo</h3>
                    </Link>
                    <nav>
                        <ul className={styles.headerNavList}>
                            <li>
                                <NavLink to="/" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                    <h3 className={styles.headerTitleASK}>Chat | </h3>
                                </NavLink>
                            </li>
                            <li className={styles.headerNavLeftMargin}>
                                <NavLink to="/qa" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                    <h3 className={styles.headerTitleASK}> Ask a question </h3>
                                </NavLink>
                            </li>
                            {/* <li className={styles.headerNavLeftMargin}>
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
                            </li> */}
                        </ul>
                    </nav>
                    <a href="imagepage.html">
                        <h4 className={styles.headerRightText}>Architecture</h4>
                    </a>
                    {useLogin && <LoginButton />}
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Layout;
