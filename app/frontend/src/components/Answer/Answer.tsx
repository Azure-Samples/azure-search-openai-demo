import { useMemo, useState } from "react";
import { Stack, IconButton, Text, Icon } from "@fluentui/react";
import DOMPurify from "dompurify";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

import styles from "./Answer.module.css";
import { ChatAppResponse, getCitationFilePath, SpeechConfig } from "../../api";
import { parseAnswerToHtml } from "./AnswerParser";
import { AnswerIcon } from "./AnswerIcon";
import { SpeechOutputBrowser } from "./SpeechOutputBrowser";
import { SpeechOutputAzure } from "./SpeechOutputAzure";

interface Props {
    answer: ChatAppResponse;
    index: number;
    speechConfig: SpeechConfig;
    isSelected?: boolean;
    isStreaming: boolean;
    onCitationClicked: (filePath: string) => void;
    onThoughtProcessClicked: () => void;
    onSupportingContentClicked: () => void;
    onFollowupQuestionClicked?: (question: string) => void;
    showFollowupQuestions?: boolean;
    showSpeechOutputBrowser?: boolean;
    showSpeechOutputAzure?: boolean;
}

export const Answer = ({
    answer,
    index,
    speechConfig,
    isSelected,
    isStreaming,
    onCitationClicked,
    onThoughtProcessClicked,
    onSupportingContentClicked,
    onFollowupQuestionClicked,
    showFollowupQuestions,
    showSpeechOutputAzure,
    showSpeechOutputBrowser
}: Props) => {
    const followupQuestions = answer.context?.followup_questions;
    const messageContent = answer.message.content;

    const [isCitationsOpen, setIsCitationsOpen] = useState(false);

    const toggleCitations = () => {
        setIsCitationsOpen(!isCitationsOpen);
    };

    const parsedAnswer = useMemo(() => parseAnswerToHtml(messageContent, isStreaming, onCitationClicked), [answer]);
    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);

    return (
        <Stack className={`${styles.answerContainer} ${isSelected && styles.selected}`} verticalAlign="space-between">
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    <AnswerIcon />
                    <div>
                        {showSpeechOutputAzure && (
                            <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                        )}
                        {showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                    </div>
                </Stack>
            </Stack.Item>

            <Stack.Item grow>
                <div className={styles.answerText}>
                    <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                </div>
            </Stack.Item>

            {!!followupQuestions?.length && showFollowupQuestions && onFollowupQuestionClicked && (
                <Stack.Item>
                    <Stack horizontal wrap className={`${!!parsedAnswer.citations.length ? styles.followupQuestionsList : ""}`} tokens={{ childrenGap: 6 }}>
                        <span className={styles.followupQuestionLearnMore}>Follow-up questions:</span>
                        {followupQuestions.map((x, i) => {
                            return (
                                <a key={i} className={styles.followupQuestion} title={x} onClick={() => onFollowupQuestionClicked(x)}>
                                    {`${x}`}
                                </a>
                            );
                        })}
                    </Stack>
                </Stack.Item>
            )}

            {!!parsedAnswer.citations.length && (
                <Stack.Item>
                    <Stack>
                        <Stack horizontal verticalAlign="center" onClick={toggleCitations} style={{ cursor: "pointer" }}>
                            <Icon iconName={isCitationsOpen ? "ChevronDown" : "ChevronRight"} className={styles.citationLearnMore} />
                            <Text className={styles.citationLearnMore}>Citations</Text>
                        </Stack>
                        {isCitationsOpen && (
                            <Stack horizontal wrap tokens={{ childrenGap: 5 }}>
                                {parsedAnswer.citations.map((x, i) => {
                                    const path = getCitationFilePath(x);
                                    return (
                                        <a key={i} className={styles.citation} title={x} onClick={() => onCitationClicked(path)}>
                                            {`${++i}. ${x}`}
                                        </a>
                                    );
                                })}
                            </Stack>
                        )}
                    </Stack>
                </Stack.Item>
            )}
            <div className={styles.disclaimerContainer}>
                <div className={styles.disclaimer}>
                    <p>
                        <b>IMPORTANT: </b>GovGPT is currently in a pilot stage and may include incomplete or incorrect content. Please ensure you check
                        citations and verify answers with the relevant cited organisations. If you notice mistakes or irrelevant responses, use the{" "}
                        <a href="https://ai-activator.circle.so/c/open-feedback-questions/" target="_blank" rel="noopener noreferrer">
                            feedback
                        </a>{" "}
                        button to let us know.
                    </p>
                </div>
            </div>
        </Stack>
    );
};
