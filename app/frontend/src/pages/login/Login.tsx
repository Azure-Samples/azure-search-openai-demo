import { useState, useEffect } from "react";
import { Button, Input } from "@fluentui/react-components";
import { useNavigate } from "react-router-dom";

import styles from "./Login.module.css";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../..";
import { Eye20Regular, EyeOff20Regular } from "@fluentui/react-icons";

export default function Login(): JSX.Element {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const [errorText, setErrorText] = useState("");
    const [stateText, setStateText] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const navigate = useNavigate();

    const signIn = () => {
        setStateText("Signing in");

        signInWithEmailAndPassword(auth, email, password)
            .then((userCredential: any) => {
                // Signed in
                setStateText("Logged in! ");
                // navigate("/");
                // console.log("Logged in: ", userCredential);
                const user = userCredential.user;
                // console.log("USER", user);

                // loggedIn()

                // successfulAuth(user.uid)
            })
            .catch(error => {
                // An error happened.
                setStateText("");
                setErrorText("Error Message");
                const errorCode = error.code;
                const errorMessage = error.message;
                console.log("ERRORTT", errorCode);
                setErrorText(errorMessage);
                if (errorCode === "auth/invalid-email") {
                    setErrorText("Error: Invalid email or username structure");
                }
                if (errorCode === "auth/user-not-found") {
                    setErrorText("Error: No account exists with this email or username");
                }
                if (errorCode === "auth/wrong-password") {
                    setErrorText("Error: This is the incorrect password for this account");
                }
            });
    };

    // useEffect(() => {
    //     if (auth.currentUser) {
    //         navigate("/");
    //     }
    // });
    return (
        <div className={styles.wrapper}>
            <div className={styles.container}>
                <h1>Login</h1>
                <div className={styles.inputColumn}>
                    <Input name="email" placeholder="Email" onChange={(e: any) => setEmail(e.target.value)} type="email" />
                    <Input
                        name="password"
                        placeholder="Password"
                        onChange={(e: any) => setPassword(e.target.value)}
                        type={showPassword ? "text" : "password"}
                        contentAfter={
                            showPassword ? (
                                <EyeOff20Regular style={{ cursor: "pointer" }} onClick={() => setShowPassword(false)} />
                            ) : (
                                <Eye20Regular
                                    style={{ cursor: "pointer" }}
                                    onClick={() => {
                                        setShowPassword(true);
                                    }}
                                />
                            )
                        }
                    />
                </div>
                <Button onClick={signIn}>Login</Button>

                <p style={{ color: "red", margin: "0px" }}>{errorText}</p>
                <p style={{ color: "green", margin: "0px" }}>{stateText}</p>
            </div>
        </div>
    );
}
