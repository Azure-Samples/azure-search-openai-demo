import { useState } from "react";
import { Stack, TextField } from "@fluentui/react";
import { Mic28Filled, Send28Filled } from "@fluentui/react-icons";

import styles from "./QuestionInput.module.css";
import * as sdk from "microsoft-cognitiveservices-speech-sdk";


interface Props {
    onSend: (question: string) => void;
    disabled: boolean;
    placeholder?: string;
    clearOnSend?: boolean;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend }: Props) => {
    const [question, setQuestion] = useState<string>("");

    const sendQuestion = () => {
        if (disabled || !question.trim()) {
            return;
        }

        onSend(question);

        if (clearOnSend) {
            setQuestion("");
        }
    };

    const startRecording = () => {
        const speechConfig = sdk.SpeechConfig.fromSubscription(
            "yoursubscriptionkey",
            "yourregion"
          );
          speechConfig.speechRecognitionLanguage = "zh-CN";
        var audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();
        var recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

        recognizer.recognizeOnceAsync(
            (result) => {
                console.log(result);
                recognizer.close();
                setQuestion(result.text);
            },
        (err) => {
            console.log(err);
            recognizer.close();
        }
);
    };

    const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            sendQuestion();
        }
    };

    const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        if (!newValue) {
            setQuestion("");
        } else if (newValue.length <= 1000) {
            setQuestion(newValue);
        }
    };

    const sendQuestionDisabled = disabled || !question.trim();
    return (
        <Stack horizontal className={styles.questionInputContainer}>
            <TextField
                className={styles.questionInputTextArea}
                placeholder={placeholder}
                multiline
                resizable={false}
                borderless
                value={question}
                onChange={onQuestionChange}
                onKeyDown={onEnterPress}
            />
            <div className={styles.questionInputButtonsContainer}>
                <div
                    className={`${styles.questionInputSendButton} ${sendQuestionDisabled ? styles.questionInputSendButtonDisabled : ""}`}
                    aria-label="Ask question button"
                    onClick={sendQuestion}
                >
                    <Send28Filled primaryFill="rgba(115, 118, 225, 1)" />
                </div>
            </div>
            <div className={styles.questionInputButtonsContainer}>
                <div
                    className={`${styles.questionAudioInputSendButton} ${sendQuestionDisabled ? styles.questionAudioInputSendButtonDisabled : ""}`}
                    aria-label="Ask question button"
                    onClick={startRecording}
                >
                    <Mic28Filled primaryFill="rgba(115, 118, 225, 1)" />
                    
                </div>
            </div>
        </Stack>
    );
};
