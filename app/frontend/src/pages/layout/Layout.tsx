import React, { useState, useEffect, useRef, RefObject } from "react";
import { Outlet, NavLink, Link } from "react-router-dom";

import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";

import { LoginButton } from "../../components/LoginButton";
import { IconButton } from "@fluentui/react";
import {
    ChatFilled,
    ChevronDownFilled,
    ChevronLeftFilled,
    ChevronRightFilled,
    Dismiss24Regular,
    NavigationFilled,
    NotebookAddFilled,
    SparkleFilled
} from "@fluentui/react-icons";
import { Button, Drawer, DrawerBody, DrawerHeader, DrawerHeaderTitle, useRestoreFocusSource, useRestoreFocusTarget } from "@fluentui/react-components";

const Layout = () => {
    // const [menuOpen, setMenuOpen] = useState(false);
    // const menuRef: RefObject<HTMLDivElement> = useRef(null);

    const [sidebarToggle, setSidebarToggle] = useState(true);
    const [drawerToggle, setDrawerToggle] = useState(false);

    // const toggleMenu = () => {
    //     setMenuOpen(!menuOpen);
    // };

    // const handleClickOutside = (event: MouseEvent) => {
    //     if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
    //         setMenuOpen(false);
    //     }
    // };

    // useEffect(() => {
    //     if (menuOpen) {
    //         document.addEventListener("mousedown", handleClickOutside);
    //     } else {
    //         document.removeEventListener("mousedown", handleClickOutside);
    //     }
    //     return () => {
    //         document.removeEventListener("mousedown", handleClickOutside);
    //     };
    // }, [menuOpen]);

    const drawerHandler = () => {
        setDrawerToggle(!drawerToggle);
    };
    const sidebarHandler = () => {
        setSidebarToggle(!sidebarToggle);
    };
    const restoreFocusTargetAttributes = useRestoreFocusTarget();
    const restoreFocusSourceAttributes = useRestoreFocusSource();

    return (
        <>
            <div className={styles.dashboardLayout}>
                <aside className={sidebarToggle ? styles.sidebar : styles.hidden}>
                    <button className={styles.sidebarToggler} onClick={sidebarHandler}>
                        <ChevronLeftFilled className={styles.sidebarTogglerIcon} />
                    </button>
                    <div className={styles.sidebarContainer}>
                        <SparkleFilled fontSize={"60px"} primaryFill={"rgba(115, 118, 225, 1)"} aria-hidden="true" aria-label="Chat logo" />
                        <Link to="/" className={styles.headerTitleContainer}>
                            <h3 className={styles.headerTitle}>Azure AI</h3>
                        </Link>
                    </div>
                    <hr className={styles.seperator} />
                    {/* Navlinks */}
                    <div className={styles.navLinks}>
                        <NavLink to="/" className={({ isActive }) => (isActive ? styles.navLinkActive : styles.headerNavPageLink)} onClick={() => {}}>
                            <span className={styles.navIconStyles}>
                                <ChatFilled fontSize={"20px"} />
                            </span>
                            <span>Chat</span>
                        </NavLink>
                        <NavLink to="/qa" className={({ isActive }) => (isActive ? styles.navLinkActive : styles.headerNavPageLink)} onClick={() => {}}>
                            <span className={styles.navIconStyles}>
                                <NotebookAddFilled fontSize={"20px"} />
                            </span>
                            Ask a question
                        </NavLink>
                    </div>
                </aside>
                <main className={sidebarToggle ? styles.main : styles.mainExpanded}>
                    <div className={styles.container}>
                        <div className={styles.navbar}>
                            <button onClick={drawerHandler} className={styles.drawerBtn} {...restoreFocusTargetAttributes}>
                                <NavigationFilled fontSize={"20px"} primaryFill={"#"} />
                            </button>
                            <div className={styles.navBrand}>
                                {!sidebarToggle && (
                                    <button className={styles.sidebarTogglerMain} onClick={sidebarHandler}>
                                        <ChevronRightFilled className={styles.sidebarTogglerIcon} />
                                    </button>
                                )}
                                <div className={styles.navHeader}>
                                    <span className={styles.navLogo}>
                                        <SparkleFilled fontSize={"20px"} primaryFill={"rgba(115, 118, 225, 1)"} aria-hidden="true" aria-label="Chat logo" />
                                    </span>
                                    <span className={styles.navbarHeaderTitle}>Azure OpenAI & AI Search</span>
                                </div>
                            </div>
                            <div>{useLogin && <LoginButton />}</div>
                        </div>
                        <Outlet />
                    </div>
                </main>
            </div>
            {/* DRAWER START */}
            <Drawer {...restoreFocusSourceAttributes} type={"overlay"} separator open={drawerToggle} onOpenChange={(_, { open }) => setDrawerToggle(open)}>
                <DrawerBody>
                    <div onClick={drawerHandler} className={drawerToggle ? styles.drawer : styles.hidden}>
                        <div className={styles.drawerNav}>
                            <button onClick={drawerHandler} className={styles.drawerBtn}>
                                <NavigationFilled fontSize={"20px"} primaryFill={"#"} />
                            </button>
                            <div className={styles.drawerMenu}>
                                <div className={styles.sidebarContainer}>
                                    <SparkleFilled fontSize={"35px"} primaryFill={"rgba(115, 118, 225, 1)"} aria-hidden="true" aria-label="Chat logo" />
                                    <Link to="/" className={styles.headerTitleContainer}>
                                        <h3 className={styles.headerTitle}>Azure AI</h3>
                                    </Link>
                                </div>
                                <hr className={styles.seperator} />
                                {/* Navlinks */}
                                <div className={styles.navLinks}>
                                    <NavLink
                                        to="/"
                                        className={({ isActive }) => (isActive ? styles.navLinkActive : styles.headerNavPageLink)}
                                        onClick={() => () => {}}
                                    >
                                        <span className={styles.navIconStyles}>
                                            <ChatFilled fontSize={"20px"} />
                                        </span>
                                        <span>Chat</span>
                                    </NavLink>
                                    <NavLink
                                        to="/qa"
                                        className={({ isActive }) => (isActive ? styles.navLinkActive : styles.headerNavPageLink)}
                                        onClick={() => {}}
                                    >
                                        <span className={styles.navIconStyles}>
                                            <NotebookAddFilled fontSize={"20px"} />
                                        </span>
                                        Ask a question
                                    </NavLink>
                                </div>
                            </div>
                        </div>
                    </div>
                </DrawerBody>
            </Drawer>
            {/* DRAWER END */}
        </>
    );
};

export default Layout;
