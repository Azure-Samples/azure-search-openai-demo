import { useState } from "react";
import { Stack, TextField } from "@fluentui/react";
import { Button, Tooltip, Field, Textarea } from "@fluentui/react-components";
import { Send28Filled } from "@fluentui/react-icons";

import styles from "./QuestionInput.module.css";
import { ChatInput } from "../../api/models";

interface Props {
    onSend: (question: string) => void;
    disabled: boolean;
    clearOnSend?: boolean;
    chatInput?: ChatInput;
}

export const QuestionInput = ({ onSend, disabled, clearOnSend, chatInput }: Props) => {
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

    const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
        if ((ev.key === "Enter" || ev.keyCode === 13) && !ev.shiftKey) {
            ev.preventDefault();
            sendQuestion();
        }
    };

    const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        if (!newValue) {
            setQuestion("");
        } else if (newValue.length <= 1000) {
            setQuestion(!chatInput || chatInput.inputType == "numeric" ? newValue?.replace(/\D/g, "") : newValue);
        }
    };

    const sendQuestionDisabled = disabled || !question.trim();

    return chatInput && chatInput.inputType == "multiple" ? (
        <Stack horizontal className={styles.questionInputContainer}>
            {chatInput.options.map(option => (
                <Button
                    style={{ backgroundColor: "#d7c5d0", borderColor: "purple", borderWidth: 2, borderStyle: "solid", borderRadius: 4, marginLeft: 10 }}
                    onClick={() => {
                        onSend(option);
                    }}
                >
                    {option}
                </Button>
            ))}
        </Stack>
    ) : (
        <form>
            <Stack horizontal className={styles.questionInputContainer}>
                <TextField
                    className={styles.questionInputTextArea}
                    placeholder={chatInput?.inputType == "numeric" ? "יש להקליד מספר" : "יש להקליד תשובה"}
                    resizable={false}
                    borderless
                    value={question}
                    onChange={onQuestionChange}
                    onKeyDown={onEnterPress}
                />
                <div className={styles.questionInputButtonsContainer}>
                    <Button
                        size="large"
                        icon={<Send28Filled primaryFill="rgba(18, 29, 59, 1)" />}
                        style={{ transform: "rotate(180deg)" }}
                        disabled={sendQuestionDisabled}
                        onClick={sendQuestion}
                    />
                </div>
            </Stack>
        </form>
    );
};
