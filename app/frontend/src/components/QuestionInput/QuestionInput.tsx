import { useState, useEffect, useContext } from "react";
import { Stack, TextField, TooltipHost, IconButton, IIconProps, initializeIcons } from "@fluentui/react";
import { Button, Tooltip } from "@fluentui/react-components";
import { Send28Filled } from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";

import styles from "./QuestionInput.module.css";
import { SpeechInput } from "./SpeechInput";
import { LoginContext } from "../../loginContext";
import { requireLogin } from "../../authConfig";

interface Props {
    onSend: (question: string) => void;
    disabled: boolean;
    initQuestion?: string;
    placeholder?: string;
    clearOnSend?: boolean;
    showSpeechInput?: boolean;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend, initQuestion, showSpeechInput }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const { loggedIn } = useContext(LoginContext);
    const { t } = useTranslation();
    const [isComposing, setIsComposing] = useState(false);

    useEffect(() => {
        initQuestion && setQuestion(initQuestion);
    }, [initQuestion]);

    const sendQuestion = () => {
        if (disabled || !question.trim()) {
            return;
        }

        onSend(question);

        if (clearOnSend) {
            setQuestion("");
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
    const sendQuestionDisabled = disabled || !question.trim() || disableRequiredAccessControl;

    if (disableRequiredAccessControl) {
        placeholder = "Please login to continue...";
    }

    return (
        <Stack
            horizontal
            className={styles.questionInputContainer}
            styles={{
                root: {
                    border: "2px solid transparent",
                    borderRadius: "6px",
                    selectors: {
                        ":focus-within": {
                            borderColor: "rgba(115, 118, 225, 1)" // Microsoft blue color
                        }
                    }
                }
            }}
        >
            <TextField
                styles={{
                    fieldGroup: {
                        height: "56px",
                        fontSize: "16px",
                        borderRadius: "4px",
                        color: "#1d1db20",
                        border: "none",
                        selectors: {
                            ":focus-within": {
                                outline: "none",
                                border: "none",
                                borderColor: "transparent"
                            },
                            "::after": {
                                border: "none",
                                outline: "none"
                            }
                        }
                    },
                    field: {
                        color: "#1d1b20",
                        fontSize: "16px",
                        padding: "12px",
                        "&:focus": {
                            outline: "none",
                            border: "none"
                        },
                        "&:focus-visible": {
                            outline: "none"
                        },
                        "&::selection": {
                            background: "rgba(0, 120, 212, 0.2)" // Keep text selection color but remove focus ring
                        }
                    },
                    wrapper: {
                        selectors: {
                            ":focus-within": {
                                outline: "none",
                                border: "none"
                            }
                        }
                    }
                }}
                className={styles.questionInputTextArea}
                disabled={disableRequiredAccessControl}
                placeholder={placeholder}
                resizable={false}
                value={question}
                onChange={onQuestionChange}
                onKeyDown={onEnterPress}
                onCompositionStart={handleCompositionStart}
                onCompositionEnd={handleCompositionEnd}
            />
            <div className={styles.questionInputButtonsContainer}>
                <Tooltip content={t("tooltips.submitQuestion")} relationship="label">
                    <Button
                        className={styles.submitButton}
                        size="large"
                        icon={<Send28Filled className={styles.iconButton} />}
                        disabled={sendQuestionDisabled}
                        onClick={sendQuestion}
                    />
                </Tooltip>
            </div>
            {showSpeechInput && <SpeechInput updateQuestion={setQuestion} />}
        </Stack>
    );
};