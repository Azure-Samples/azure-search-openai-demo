import { useState, useEffect, useContext, useRef } from "react";
import { Stack, TextField } from "@fluentui/react";
import { Button, Tooltip } from "@fluentui/react-components";
import { Send28Filled, Image24Regular } from "@fluentui/react-icons";

import styles from "./QuestionInput.module.css";
import { SpeechInput } from "./SpeechInput";
import { LoginContext } from "../../loginContext";
import { requireLogin } from "../../authConfig";

interface Props {
    onSend: (question: string, image?: string) => void; // URL of the image updated with the question
    disabled: boolean;
    initQuestion?: string;
    placeholder?: string;
    clearOnSend?: boolean;
    showSpeechInput?: boolean;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend, initQuestion, showSpeechInput }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const { loggedIn } = useContext(LoginContext);
    const [isComposing, setIsComposing] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null); // New state for file
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [uploadeFileUrl, setUploadedFileUrl] = useState<string | undefined>(undefined);

    useEffect(() => {
        initQuestion && setQuestion(initQuestion);
    }, [initQuestion]);

    const sendQuestion = () => {
        if (disabled || !question.trim()) {
            return;
        }

        console.log("Uploaded file url we are sending is ...", uploadeFileUrl);
        onSend(question, uploadeFileUrl); // Pass the selected file or undefined

        if (clearOnSend) {
            setQuestion("");
            setSelectedFile(null); // Clear the file on send
            setUploadedFileUrl(undefined);
        }
    };

    const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
        if (isComposing) return;

        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            sendQuestion();
        }
    };

    const handleCompositionStart = () => {
        setIsComposing(true);
    };
    const handleCompositionEnd = () => {
        setIsComposing(false);
    };

    const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        if (!newValue) {
            setQuestion("");
        } else if (newValue.length <= 1000) {
            setQuestion(newValue);
        }
    };

    const disableRequiredAccessControl = requireLogin && !loggedIn;
    const sendQuestionDisabled = disabled || !question.trim() || requireLogin;

    if (disableRequiredAccessControl) {
        placeholder = "Please login to continue...";
    }

    const handleImageUpload = () => {
        fileInputRef.current?.click();
    };

    const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await fetch("/upload_new", {
                    method: "POST",
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log("File uploaded successfully:", result.message);
                    // You might want to update the UI to show the uploaded image name
                    console.log("Blob url received is ", result.file_url);
                    setUploadedFileUrl(result.file_url);
                    console.log("Set varaible value is ", uploadeFileUrl);
                } else {
                    console.error("File upload failed");
                    setUploadedFileUrl(undefined);
                }
            } catch (error) {
                console.error("Error uploading file:", error);
                setUploadedFileUrl(undefined);
            }
        }
    };

    return (
        <Stack horizontal className={styles.questionInputContainer}>
            <TextField
                className={styles.questionInputTextArea}
                disabled={disableRequiredAccessControl}
                placeholder={placeholder}
                multiline
                resizable={false}
                borderless
                value={question}
                onChange={onQuestionChange}
                onKeyDown={onEnterPress}
                onCompositionStart={handleCompositionStart}
                onCompositionEnd={handleCompositionEnd}
            />
            <input type="file" onChange={onFileChange} accept="image/*" /> {/* New file input */}
            <div className={styles.questionInputButtonsContainer}>
                <Tooltip content="Submit question" relationship="label">
                    <Button size="large" icon={<Send28Filled primaryFill="rgba(115, 118, 225, 1)" />} disabled={sendQuestionDisabled} onClick={sendQuestion} />
                </Tooltip>
            </div>
            {showSpeechInput && <SpeechInput updateQuestion={setQuestion} />}
        </Stack>
    );
};
