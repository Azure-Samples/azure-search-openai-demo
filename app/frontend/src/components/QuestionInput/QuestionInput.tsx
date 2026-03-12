import { useState, useEffect, useContext, useCallback, useRef } from "react";
import { Button, Textarea, Tooltip } from "@fluentui/react-components";
import { Send28Filled } from "@fluentui/react-icons";
import { useTranslation } from "react-i18next";

import styles from "./QuestionInput.module.css";
import { SpeechInput } from "./SpeechInput";
import { LoginContext } from "../../loginContext";
import { requireLogin } from "../../authConfig";

const StopCircleIcon = () => (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="14" cy="14" r="12.5" stroke="black" strokeWidth="2" fill="none" />
        <rect x="9" y="9" width="10" height="10" rx="1" fill="black" />
    </svg>
);

interface Props {
    onSend: (question: string) => void;
    disabled: boolean;
    initQuestion?: string;
    placeholder?: string;
    clearOnSend?: boolean;
    showSpeechInput?: boolean;
    onStop: () => void;
    isStreaming: boolean;
    isLoading: boolean;
}

export const QuestionInput = ({ onSend, onStop, disabled, placeholder, clearOnSend, initQuestion, showSpeechInput, isStreaming, isLoading }: Props) => {
    const [question, setQuestion] = useState<string>("");
    const { loggedIn } = useContext(LoginContext);
    const { t } = useTranslation();
    const [isComposing, setIsComposing] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const autoResize = useCallback(() => {
        const el = textareaRef.current;
        if (!el) return;
        const wrapper = el.parentElement;
        el.style.height = "auto";
        const maxH = wrapper ? parseFloat(getComputedStyle(wrapper).maxHeight) : Infinity;
        const atMax = el.scrollHeight > maxH;
        el.style.height = (atMax ? maxH : el.scrollHeight) + "px";
        el.style.overflowY = atMax ? "auto" : "hidden";
        if (wrapper) wrapper.style.overflow = atMax ? "visible" : "hidden";
    }, []);

    useEffect(() => {
        autoResize();
    }, [question, autoResize]);

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

    const onQuestionChange = (_ev: React.ChangeEvent<HTMLTextAreaElement>, data: { value: string }) => {
        setQuestion(data.value);
    };

    const disableRequiredAccessControl = requireLogin && !loggedIn;
    const sendQuestionDisabled = disabled || !question.trim() || disableRequiredAccessControl;

    if (disableRequiredAccessControl) {
        placeholder = "Please login to continue...";
    }

    return (
        <div className={styles.questionInputContainer} style={{ display: "flex", gap: "0.25rem" }}>
            <Textarea
                textarea={{ ref: textareaRef }}
                className={styles.questionInputTextArea}
                disabled={disableRequiredAccessControl}
                placeholder={placeholder}
                resize="none"
                value={question}
                onChange={onQuestionChange}
                onKeyDown={onEnterPress}
                onCompositionStart={handleCompositionStart}
                onCompositionEnd={handleCompositionEnd}
            />
            <div className={styles.questionInputButtonsContainer}>
                {isStreaming || isLoading ? (
                    <Tooltip content={t("tooltips.stopStreaming")} relationship="label">
                        <Button size="large" icon={<StopCircleIcon />} onClick={onStop} />
                    </Tooltip>
                ) : (
                    <Tooltip content={t("tooltips.submitQuestion")} relationship="label">
                        <Button
                            size="large"
                            icon={<Send28Filled primaryFill="rgba(115, 118, 225, 1)" />}
                            disabled={sendQuestionDisabled}
                            onClick={sendQuestion}
                        />
                    </Tooltip>
                )}
            </div>
            {showSpeechInput && <SpeechInput updateQuestion={setQuestion} />}
        </div>
    );
};
