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
import { useNavigate, useLocation } from "react-router-dom";

const Layout = () => {
    const navigate = useNavigate();
    const currentUser = useLocation().state;
    const baseURL = import.meta.env.VITE_FIREBASE_BASE_URL;
    const [loggedIn, setLoggedIn] = useState(false);
    const [userData, setUserData] = useState<User>({
        uuid: "",
        emailAddress: "",
        firstName: "",
        lastName: "",
        initialPasswordChanged: null
    });
    const [noProjects, setNoProjects] = useState(false);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, user => {
            if (user) {
                axios.get(baseURL + "getProjects", { params: { clientID: user.uid } }).then(response => {
                    getAccountDetail(user.uid);
                    setLoggedIn(true);
                    if (response.data.length === 0) {
                        navigate("/no-projects", {});
                        setNoProjects(true);
                    } else {
                        if (userData.initialPasswordChanged === false) {
                            navigate("../change-password", {});
                        } else {
                            navigate("/", { state: userData });
                        }
                    }
                });
            } else {
                setUserData({
                    uuid: "",
                    emailAddress: "",
                    firstName: "",
                    lastName: "",
                    initialPasswordChanged: null
                });
                navigate("../login", {});
                setLoggedIn(false);
            }
        });
        return () => unsubscribe();
    }, []);

    useEffect(() => {
        if (window.location.hash === "#/" || window.location.hash === "#/manage") {
            if (userData.uuid === "") {
                navigate("/login", {});
            }
            if (noProjects) {
                navigate("/no-projects", { state: userData });
            }
            if (userData.initialPasswordChanged === false) {
                navigate("/change-password", { state: userData });
            }
        }
    }, [userData]);

    useEffect(() => {
        if (currentUser && currentUser.userData) {
            setUserData(currentUser.userData);
        }
    }, [currentUser]);

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
                setUserData({
                    uuid: "",
                    emailAddress: "",
                    firstName: "",
                    lastName: "",
                    initialPasswordChanged: false
                });
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
                    <Link to={userData.uuid ? "/" : "/login"} className={styles.headerTitleContainer}>
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
