import React, { useState, useEffect, useRef, RefObject } from "react";
import { Outlet, NavLink, Link } from "react-router-dom";

import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";
import { LoginButton } from "../../components/LoginButton";
import { IconButton } from "@fluentui/react";
import FeedbackButton from "../../components/FeedbackButton/FeedbackButton";

const Layout = () => {
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef: RefObject<HTMLDivElement> = useRef(null);

    const toggleMenu = () => {
        setMenuOpen(!menuOpen);
    };

    const handleClickOutside = (event: MouseEvent) => {
        if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
            setMenuOpen(false);
        }
    };

    useEffect(() => {
        if (menuOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        } else {
            document.removeEventListener("mousedown", handleClickOutside);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [menuOpen]);

    return (
        <div className={styles.layout}>
            <header className={styles.header} role="banner">
                <div className={styles.headerContainer} ref={menuRef}>
                    <h3 className={styles.headerTitle}>GovGPT - Pilot</h3>
                    <div className={styles.headerRight}>
                        <img src="/CI_Logo_Powered_green.png" alt="description of image" className={styles.headerImg} />
                        <FeedbackButton />
                    </div>
                </div>
            </header>
            <Outlet />
        </div>
    );
};

export default Layout;
