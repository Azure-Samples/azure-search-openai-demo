import { SetStateAction, useState } from "react";
import { Button, Tooltip } from "@fluentui/react-components";
import { Mic28Filled } from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";
import styles from "./QuestionInput.module.css";
import { supportedLngs } from "../../i18n/config";

interface Props {
    updateQuestion: (question: string) => void;
}

const useCustomSpeechRecognition = () => {
    const { i18n } = useTranslation();
    const currentLng = i18n.language;
    let lngCode = supportedLngs[currentLng]?.locale;
    if (!lngCode) {
        lngCode = "en-US";
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    let speechRecognition: {
        continuous: boolean;
        lang: string;
        interimResults: boolean;
        maxAlternatives: number;
        start: () => void;
        onresult: (event: { results: { transcript: SetStateAction<string> }[][] }) => void;
        onend: () => void;
        onerror: (event: { error: string }) => void;
        stop: () => void;
    } | null = null;

    try {
        speechRecognition = new SpeechRecognition();
        if (speechRecognition != null) {
            speechRecognition.lang = lngCode;
            speechRecognition.interimResults = true;
        }
    } catch (err) {
        console.error("SpeechRecognition not supported");
        speechRecognition = null;
    }

    return speechRecognition;
};

export const SpeechInput = ({ updateQuestion }: Props) => {
    let speechRecognition = useCustomSpeechRecognition();
    const { t } = useTranslation();
    const [isRecording, setIsRecording] = useState<boolean>(false);
    const startRecording = () => {
        if (speechRecognition == null) {
            console.error("SpeechRecognition not supported");
            return;
        }

        speechRecognition.onresult = (event: { results: { transcript: SetStateAction<string> }[][] }) => {
            let input = "";
            for (const result of event.results) {
                input += result[0].transcript;
            }
            updateQuestion(input);
        };
        speechRecognition.onend = () => {
            // NOTE: In some browsers (e.g. Chrome), the recording will stop automatically after a few seconds of silence.
            setIsRecording(false);
        };
        speechRecognition.onerror = (event: { error: string }) => {
            if (speechRecognition) {
                speechRecognition.stop();
                if (event.error == "no-speech") {
                    alert("No speech was detected. Please check your system audio settings and try again.");
                } else if (event.error == "language-not-supported") {
                    alert(
                        `Speech recognition error detected: ${event.error}. The speech recognition input functionality does not yet work on all browsers, like Edge in Mac OS X with ARM chips. Try another browser/OS.`
                    );
                } else {
                    alert(`Speech recognition error detected: ${event.error}.`);
                }
            }
        };

        setIsRecording(true);
        speechRecognition.start();
    };

    const stopRecording = () => {
        if (speechRecognition == null) {
            console.error("SpeechRecognition not supported");
            return;
        }
        speechRecognition.stop();
        setIsRecording(false);
    };

    if (speechRecognition == null) {
        return <></>;
    }
    return (
        <>
            {!isRecording && (
                <div className={styles.questionInputButtonsContainer}>
                    <Tooltip content={t("tooltips.askWithVoice")} relationship="label">
                        <Button size="large" icon={<Mic28Filled primaryFill="rgba(115, 118, 225, 1)" />} onClick={startRecording} />
                    </Tooltip>
                </div>
            )}
            {isRecording && (
                <div className={styles.questionInputButtonsContainer}>
                    <Tooltip content={t("tooltips.stopRecording")} relationship="label">
                        <Button size="large" icon={<Mic28Filled primaryFill="rgba(250, 0, 0, 0.7)" />} disabled={!isRecording} onClick={stopRecording} />
                    </Tooltip>
                </div>
            )}
        </>
    );
};
