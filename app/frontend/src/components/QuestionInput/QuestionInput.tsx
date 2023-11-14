import { useState } from "react";
import { Stack, TextField, Dropdown, IDropdownOption } from "@fluentui/react";
import { Button, Tooltip, Option } from "@fluentui/react-components";
import { Send28Filled } from "@fluentui/react-icons";
import styles from "./QuestionInput.module.css";

interface Props {
    onSend: (question: string, contextIndex: string) => void;
    disabled: boolean;
    placeholder?: string;
    clearOnSend?: boolean;
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const [contextIndex, setContextIndex] = useState<string>("");

    const contextOptions = [{ id: 1, name: "Red" }, { id: 2, name: "Blue" }, { id: 3, name: "Green" }]

    const sendQuestion = () => {
        if (disabled || !question.trim()) {
            return;
        }

        onSend(question, contextIndex);

        if (clearOnSend) {
            setQuestion("");
        }
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


    const onContextChange = (_ev, option, index?: number | undefined) => {
        setContextIndex(option?.data);
    };

    return (
        <div>
            <Dropdown
                required
                label="Context"
                placeholder="Select context"
                onChange={onContextChange}
                options={[{ key: 'index_1', text: 'Red', data: 'red' }, { key: 'index_2', text: 'Blue', data: 'Blue' }]}
            />
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
                    <Tooltip content="Ask question button" relationship="label">
                        <Button size="large" icon={<Send28Filled primaryFill="rgba(115, 118, 225, 1)" />} disabled={sendQuestionDisabled} onClick={sendQuestion} />
                    </Tooltip>
                </div>
            </Stack>
        </div>
    );
};
