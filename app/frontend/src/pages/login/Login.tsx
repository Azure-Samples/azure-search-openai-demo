import { useState, useEffect, FormEventHandler, FormEvent } from "react";
import {
    TableBody,
    TableCell,
    TableRow,
    Table,
    TableHeader,
    TableHeaderCell,
    Accordion,
    AccordionItem,
    AccordionHeader,
    AccordionPanel,
    Button,
    Dialog,
    DialogTrigger,
    DialogSurface,
    DialogTitle,
    DialogBody,
    DialogActions,
    DialogContent,
    Input,
    Label,
    Dropdown,
    Option,
    TableCellLayout
} from "@fluentui/react-components";

import "./Login.css";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../..";


export default function Login(): JSX.Element {
    

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const [errorText, setErrorText] = useState("");


    const signIn = () => {

        setErrorText("Signing in")

        signInWithEmailAndPassword(auth, email, password)
            .then((userCredential:any) => {
                // Signed in 
                setErrorText("Logged in! ")
                console.log("Logged in: ", userCredential)
                const user = userCredential.user;
                console.log("USER", user)


                // loggedIn()

                // successfulAuth(user.uid)
            })
            .catch((error) => {
                // An error happened.
                setErrorText("Error MEssage")
                const errorCode = error.code;
                const errorMessage = error.message;
                console.log("ERRORTT", errorCode)
                setErrorText(errorMessage)
                if (errorCode === "auth/invalid-email") { setErrorText("Error: Invalid email or username structure") }
                if (errorCode === "auth/user-not-found") { setErrorText("Error: No account exists with this email or username") }
                if (errorCode === "auth/wrong-password") { setErrorText("Error: This is the incorrect password for this account") }
            });

    }


    return (
        <div className="column ai-centre padding80 gap20" >
            <h1>Login</h1>
            <Input name="email" placeholder="Email" onChange={(e:any) => setEmail(e.target.value)} type="email"/>
            <Input name="password" placeholder="Password" onChange={(e:any) => setPassword(e.target.value)}  type="password"/>

            <Button onClick={signIn}>Login</Button>

            <span>{errorText}</span>
        </div>
    );
}
