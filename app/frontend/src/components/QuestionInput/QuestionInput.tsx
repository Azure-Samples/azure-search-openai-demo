import { ChangeEvent, useEffect, useState, useRef } from "react";
import { useMsal } from "@azure/msal-react";
import { IStyleFunctionOrObject, Stack, TextField } from "@fluentui/react";
import { Button, Tooltip, Spinner } from "@fluentui/react-components";
import { Toggle } from "@fluentui/react/lib/Toggle";
import { Send24Filled, ArrowUpload24Filled, ArrowClockwise24Regular, ArrowClockwise24Filled } from "@fluentui/react-icons";
import { isLoggedIn, requireAccessControl } from "../../authConfig";

import styles from "./QuestionInput.module.css";
import UploadFiles from "../UploadFiles/UploadFiles";

interface Props {
    onSend: (question: string) => void;
    setDocFilter: (docs: string | undefined) => void;
    disabled: boolean;
    initQuestion?: string;
    placeholder?: string;
    clearOnSend?: boolean;
}

export const QuestionInput = ({ onSend, setDocFilter, disabled, placeholder, clearOnSend, initQuestion }: Props) => {
    const [question, setQuestion] = useState<string>("");

    const [isOn, setIsOn] = useState<boolean>(true);
    const [uploadedFiles, setUploadedFiles] = useState<File[] | null>(null);

    useEffect(() => {
        initQuestion && setQuestion(initQuestion);
    }, [initQuestion]);

    useEffect(() => {
        if (isOn && uploadedFiles) {
            constructAndSetDocFilter();
        } else {
            setDocFilter(undefined);
        }
    }, [isOn, uploadedFiles]);

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

    const constructAndSetDocFilter = () => {
        if (uploadedFiles && isOn) {
            const names = uploadedFiles.map(file => file.name);

            console.log("Names", names);
            console.log("Uploaded files", uploadedFiles);

            if (names.length === 1) {
                setDocFilter(names[0]);
            } else {
                const str: string = names.join(" OR ");
                setDocFilter(str);
            }
        }
    };

    // const toggleStyles: IStyleFunctionOrObject<any, any> = {
    //     pillUncheckedBackground: {
    //         backgroundColor: "white"
    //     },
    //     pillCheckedBackground: {
    //         backgroundColor: "black"
    //     }
    // };

    const { instance } = useMsal();
    const disableRequiredAccessControl = requireAccessControl && !isLoggedIn(instance);
    const sendQuestionDisabled = disabled || !question.trim() || disableRequiredAccessControl;

    if (disableRequiredAccessControl) {
        placeholder = "Please login to continue...";
    }

    return (
        <Stack horizontal className={styles.inputUpload}>
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
                />
                <div className={styles.questionInputButtonsContainer}>
                    <Tooltip content="Ask question button" relationship="label">
                        <Button
                            size="large"
                            icon={<Send24Filled primaryFill="rgba(115, 118, 225, 1)" />}
                            disabled={sendQuestionDisabled}
                            onClick={sendQuestion}
                        />
                    </Tooltip>
                </div>
            </Stack>
            <div className={styles.uploadButtonContainer}>
                {/* <UploadFiles setUploadedFiles={setUploadedFiles} /> */}
                {!uploadedFiles && <UploadFiles setUploadedFiles={setUploadedFiles} />}
                {uploadedFiles && (
                    <div>
                        {/* <Toggle checked={isOn} styles={toggleStyles} onChange={() => setIsOn(!isOn)} label="Filter" /> */}
                        <Tooltip content="Remove all files" relationship="label">
                            <Button
                                size="large"
                                icon={<ArrowClockwise24Filled primaryFill="rgba(115, 118, 225, 1)" />}
                                onClick={() => setUploadedFiles(null)}
                            />
                        </Tooltip>
                    </div>
                )}
            </div>
        </Stack>
    );
};
