import { useMemo, useState } from "react";
import { Stack, IconButton } from "@fluentui/react";
import DOMPurify from "dompurify";
import { v4 as uuidv4 } from "uuid";
import { useMutation } from "react-query";

import styles from "./Answer.module.css";

import { ChatAppResponse, getCitationFilePath, postFeedbackApi, Feedback } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { parseAnswerToHtml, removeCitations } from "./AnswerParser";
import { AnswerIcon } from "./AnswerIcon";

interface Props {
    answer: ChatAppResponse;
    question: string;
    isSelected?: boolean;
    isStreaming: boolean;
}

const SummarizeAnswer = ({ answer, question, isSelected, isStreaming }: Props) => {
    const messageContent = answer.choices[0].message.content;
    // const parsedAnswer = useMemo(() => parseAnswerToHtml(messageContent, isStreaming), [answer]);
    const removeCitationsAnswer = removeCitations(answer.choices[0].message.content);
    // const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);

    return (
        <Stack className={`${styles.answerContainer} ${isSelected && styles.selected}`} verticalAlign="space-between">
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    <AnswerIcon />
                </Stack>
            </Stack.Item>

            <Stack.Item grow>
                <div className={styles.answerText} dangerouslySetInnerHTML={{ __html: removeCitationsAnswer }}></div>
            </Stack.Item>
        </Stack>
    );
};
export default SummarizeAnswer;
