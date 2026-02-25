import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { consentStorageKey } from "./ConsentGuard";
import styles from "./Consent.module.css";

const Consent = () => {
    const navigate = useNavigate();
    const [redirecting, setRedirecting] = useState(false);

    const handleConsentYes = () => {
        localStorage.setItem(consentStorageKey, "true");
        navigate("/chat");
    };

    const handleConsentNo = () => {
        setRedirecting(true);
        window.location.assign("https://www.au.dk/");
    };

    return (
        <section className={styles.container}>
            <article className={styles.card}>
                <h1 className={styles.title}>Consent Form for Using the Customized Chatbot "Phil"</h1>

                <h2 className={styles.sectionTitle}>Research Team, Purpose and Contact Information</h2>
                <p>
                    This project is conducted by a research team led by Carsten Bergenholtz and Oana Vuculescu (OV)
                    as key members. The research team will process and analyze the data collected.
                </p>
                <p>
                    The purpose is to learn from how users engage with the customized chatbot, in order to improve
                    future versions and potentially publish research based on the analysis. Data may also be analyzed
                    for educational purposes (for example, student exams) by members of the research team under the
                    same confidentiality conditions.
                </p>
                <p>
                    If you have any questions or concerns about the project and the processing of data, please contact
                    OV at <a href="mailto:oanav@mgmt.au.dk">oanav@mgmt.au.dk</a>.
                </p>

                <h2 className={styles.sectionTitle}>Project Support</h2>
                <p>This project is supported by It-vest and Aarhus University.</p>

                <h2 className={styles.sectionTitle}>Data Handling</h2>
                <p>
                    All data collected in this project is anonymized when storing the data, ensuring your privacy. We
                    track no particular prompt back to any user. The results will be presented in aggregate form, with
                    completely anonymous data.
                </p>
                <p>
                    Please do not enter any sensitive or personal information in your interactions with the chatbot.
                </p>

                <h2 className={styles.sectionTitle}>Consent Acknowledgement</h2>
                <p>By selecting "Yes" below, you acknowledge that:</p>
                <ul className={styles.list}>
                    <li>You understand the purpose of the study and agree to participate.</li>
                    <li>
                        You are aware that your data will be anonymized and that results will only be presented in an
                        aggregated, anonymous form.
                    </li>
                </ul>
                <p>
                    If you do not consent, you can use the version of the customized chatbot offered in 2024. Please
                    contact OV for a link.
                </p>

                <div className={styles.actions}>
                    <button className={styles.primaryButton} onClick={handleConsentYes} type="button">
                        Yes, I consent to participate in this study.
                    </button>
                    <button className={styles.secondaryButton} onClick={handleConsentNo} type="button" disabled={redirecting}>
                        No, I do not consent to participate in this study.
                    </button>
                </div>
            </article>
        </section>
    );
};

export default Consent;
