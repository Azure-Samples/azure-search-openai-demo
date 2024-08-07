import { Outlet, NavLink, Link } from "react-router-dom";

import github from "../../assets/github.svg";

import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";

import { LoginButton } from "../../components/LoginButton";
import React, { useEffect, useState } from "react";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { auth } from "../..";
import axios from "axios";
import { Button } from "@fluentui/react-components";
import { useNavigate } from "react-router-dom";

interface User {
    uuid: string;
    emailAddress: string;
    firstName: string;
    lastName: string;
    initialPasswordChanged: boolean;
    projectName?: string;
    projectId?: string;
    projectRole?: string;
}

const Layout = () => {
    const navigate = useNavigate();

    const baseURL = "https://us-central1-projectpalai-83a5f.cloudfunctions.net/";
    const [loggedIn, setLoggedIn] = useState(false);
    const [userData, setUserData] = useState<User>({
        uuid: "",
        emailAddress: "",
        firstName: "",
        lastName: "",
        initialPasswordChanged: false
    });
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, user => {
            if (user) {
                if (window.location.hash === "#/manage") {
                    setLoggedIn(true);
                    getAccountDetail(user.uid);
                }
                if (window.location.hash === "#/login") {
                    navigate("../", {});
                    setLoggedIn(true);
                }
            } else {
                navigate("../login", {});
                setLoggedIn(false);
            }
        });
        return () => unsubscribe();
    }, []);

    const getAccountDetail = (uid: string) => {
        axios
            .get(baseURL + "getAccountDetails", {
                params: {
                    clientID: uid
                }
            })
            .then(response => {
                const data = response.data;
                if (data.found) {
                    // setUserDetails(data.user)
                    localStorage.setItem("user", JSON.stringify(data.user));
                    setUserData(data.user);
                    console.log("User details: ", data.user);
                }
            });
    };

    const logout = () => {
        signOut(auth)
            .then(() => {
                // Sign-out successful.
            })
            .catch(error => {
                // An error happened.
                console.log("ERROR: ", error.message);
            });
    };

    return (
        <div className={styles.layout}>
            <div className={styles.header}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <h3 className={styles.headerTitle}>Project Pal AI</h3>
                    </Link>

                    {loggedIn && <Button onClick={logout}>Log out</Button>}

                    {useLogin && <LoginButton />}
                </div>
            </div>

            <Outlet />
        </div>
    );
};

export default Layout;
