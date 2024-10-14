import React, { useRef } from "react";
import { Example } from "./Example";
import ReCAPTCHA from "react-google-recaptcha";
import styles from "./Example.module.css";

const Types: string[] = ["Questions", "Features", "Limitations"];

interface Props {
    onExampleClicked: (value: string, token: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    const recaptchaRef = useRef<ReCAPTCHA>(null);

    const handleClick = async (value: string) => {
        if (recaptchaRef.current) {
            try {
                const token = await recaptchaRef.current.executeAsync();
                if (token) {
                    recaptchaRef.current.reset();
                    onExampleClicked(value, token);
                } else {
                    console.error("reCAPTCHA token is null");
                    alert("reCAPTCHA verification failed. Please try again.");
                }
            } catch (error) {
                console.error("reCAPTCHA execution error:", error);
                alert("reCAPTCHA timed out. Please try again.");
            }
        }
    };

    return (
        <>
            <ReCAPTCHA sitekey="6LfMIV4qAAAAAPg4D_EMBKndtGzO6xDlzCO8vQTv" size="invisible" ref={recaptchaRef} />
            <ul className={styles.examplesNavList}>
                {Types.map((value, i) => (
                    <li key={i}>
                        <Example exampleType={value} onClick={() => handleClick(value)} />
                    </li>
                ))}
            </ul>
        </>
    );
};
