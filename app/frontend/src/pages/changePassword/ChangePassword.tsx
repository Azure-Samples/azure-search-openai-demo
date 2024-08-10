import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Input, Button, Spinner } from "@fluentui/react-components";
import { Eye20Regular, EyeOff20Regular, Checkmark20Filled, Dismiss20Filled } from "@fluentui/react-icons";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../..";
import axios from "axios";

import styles from "./ChangePassword.module.css";

export function Component(): JSX.Element {
    const [userData, setUserData] = useState<User | null>(null);
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [viewPassword, setViewPassword] = useState(false);
    const [viewConfirmPassword, setViewConfirmPassword] = useState(false);
    const [errorText, setErrorText] = useState("");
    const [successText, setSuccessText] = useState("");
    const [loadingText, setLoadingText] = useState("");

    const baseURL = import.meta.env.VITE_FIREBASE_BASE_URL;
    const navigate = useNavigate();
    const currentUser = useLocation().state;

    const changePassword = () => {
        if (userData) {
            axios.post(baseURL + "updatePassword", { uid: userData.uuid, password: password }).then(response => {
                if (response.data.error === false) {
                    setErrorText("");
                    setLoadingText("");
                    setSuccessText("Password Updated");
                    setUserData({ ...userData, initialPasswordChanged: true });
                    setTimeout(() => {
                        navigate("../", { state: { ...userData, initialPasswordChanged: true } });
                    }, 4000);
                }
            });
        }
    };
    const handlePasswordSubmit = (e: any) => {
        e.preventDefault();

        let errorType = "";
        if (password !== confirmPassword) {
            errorType = "mismatch";
        } else if (password.length < 8) {
            errorType = "short";
        } else if (password === "") {
            errorType = "empty";
        }

        switch (errorType) {
            case "mismatch":
                setErrorText("Passwords do not match");
                break;
            case "short":
                setErrorText("Password must be at least 8 characters long");
                break;
            case "empty":
                setErrorText("Password cannot be empty");
                break;
            default:
                setLoadingText("Changing Password");
                changePassword();
                break;
        }
    };
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, user => {
            if (user) {
                axios.get(baseURL + "getAccountDetails", { params: { clientID: user.uid } }).then(response => {
                    const data = response.data;
                    if (data.found) {
                        setUserData(data.user);
                    }
                });
            }
        });
        return () => unsubscribe();
    }, []);

    useEffect(() => {
        if (currentUser && currentUser.userData) {
            setUserData(currentUser.userData);
        }
    }, [currentUser]);

    return (
        <div className={styles.wrapper}>
            <div className={styles.container}>
                <h1>Change Password</h1>
                <h3>Before accessing the service, you must change your password</h3>
                <h3>Please fill out the form below to reset your password to one of your choosing</h3>
                <div>
                    <form onSubmit={handlePasswordSubmit} className={styles.inputColumn}>
                        <Input
                            name="password"
                            placeholder="New Password"
                            type={viewPassword ? "text" : "password"}
                            contentAfter={
                                viewPassword ? (
                                    <EyeOff20Regular onClick={() => setViewPassword(false)} />
                                ) : (
                                    <Eye20Regular onClick={() => setViewPassword(true)} />
                                )
                            }
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                        />
                        <Input
                            name="password"
                            placeholder="Confirm Password"
                            type={viewConfirmPassword ? "text" : "password"}
                            contentAfter={
                                viewConfirmPassword ? (
                                    <EyeOff20Regular onClick={() => setViewConfirmPassword(false)} />
                                ) : (
                                    <Eye20Regular onClick={() => setViewConfirmPassword(true)} />
                                )
                            }
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirmPassword(e.target.value)}
                        />

                        <Button type="submit" appearance="primary">
                            Change Password
                        </Button>
                    </form>

                    <div className={styles.stateColumnContainer}>
                        <div className={styles.stateColumn}>
                            {loadingText && <Spinner label={loadingText} size="extra-tiny" />}
                            {errorText && (
                                <p style={{ color: "red", display: "flex", margin: "0px" }}>
                                    <Dismiss20Filled style={{ color: "red" }} />
                                    {errorText}
                                </p>
                            )}
                            {successText && (
                                <p style={{ color: "green", display: "flex", margin: "0px" }}>
                                    <Checkmark20Filled style={{ color: "green" }} />
                                    {successText}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

Component.displayName = "ChangePassword";
