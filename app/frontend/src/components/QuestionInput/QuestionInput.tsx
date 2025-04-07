import { useState, useEffect, useContext } from "react";
import { Stack, TextField } from "@fluentui/react";
import { Button, Tooltip } from "@fluentui/react-components";
import { Send28Filled, ImageAdd24Filled } from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";

import styles from "./QuestionInput.module.css";
import { SpeechInput } from "./SpeechInput";
import { LoginContext } from "../../loginContext";
import { requireLogin } from "../../authConfig";

interface Props {
    onSend: (question: string, images: File[]) => void; // Updated to include images
    disabled: boolean;
    initQuestion?: string;
    placeholder?: string;
    clearOnSend?: boolean;
    showSpeechInput?: boolean;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend, initQuestion, showSpeechInput }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const [images, setImages] = useState<File[]>([]); // State for uploaded images
    const { loggedIn } = useContext(LoginContext);
    const { t } = useTranslation();
    const [isComposing, setIsComposing] = useState(false);

    useEffect(() => {
        initQuestion && setQuestion(initQuestion);
    }, [initQuestion]);

    const sendQuestion = () => {
        if (disabled || (!question.trim() && images.length === 0)) {
            return;
        }

        onSend(question, images); // Send both text and images

        if (clearOnSend) {
            setQuestion("");
            setImages([]); // Clear images after sending
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

    const onImageUpload = (ev: React.ChangeEvent<HTMLInputElement>) => {
        if (ev.target.files) {
            setImages([...images, ...Array.from(ev.target.files)]); // Add uploaded images to state
        }
    };

    const removeImage = (index: number) => {
        setImages(images.filter((_, i) => i !== index)); // Remove an image by index
    };

    const disableRequiredAccessControl = requireLogin && !loggedIn;
    const sendQuestionDisabled = disabled || (!question.trim() && images.length === 0) || disableRequiredAccessControl;

    if (disableRequiredAccessControl) {
        placeholder = "Please login to continue...";
    }

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
            <div className={styles.questionInputButtonsContainer}>
                <Tooltip content={t("tooltips.uploadImage")} relationship="label">
                    <Button
                        size="large"
                        icon={<ImageAdd24Filled />}
                        onClick={() => document.getElementById("image-upload")?.click()}
                    />
                </Tooltip>
                <input
                    id="image-upload"
                    type="file"
                    accept="image/*"
                    multiple
                    style={{ display: "none" }}
                    onChange={onImageUpload}
                />
                <Tooltip content={t("tooltips.submitQuestion")} relationship="label">
                    <Button
                        size="large"
                        icon={<Send28Filled primaryFill="rgba(115, 118, 225, 1)" />}
                        disabled={sendQuestionDisabled}
                        onClick={sendQuestion}
                    />
                </Tooltip>
            </div>
            {showSpeechInput && <SpeechInput updateQuestion={setQuestion} />}
            <div className={styles.imagePreviewContainer}>
                {images.map((image, index) => (
                    <div key={index} className={styles.imagePreview}>
                        <img src={URL.createObjectURL(image)} alt={`Uploaded ${index}`} />
                        <button onClick={() => removeImage(index)}>Remove</button>
                    </div>
                ))}
            </div>
        </Stack>
    );
};