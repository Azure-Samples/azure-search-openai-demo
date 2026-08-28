import { useMemo, useState } from "react";
import { Stack } from "@fluentui/react";
import { useTranslation } from "react-i18next";
import DOMPurify from "dompurify";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

import styles from "./Answer.module.css";
import { ChatAppResponse, SpeechConfig } from "../../api";
import { parseAnswerToHtml } from "./AnswerParser";
import { AnswerIcon } from "./AnswerIcon";
import { SpeechOutputBrowser } from "./SpeechOutputBrowser";
import { SpeechOutputAzure } from "./SpeechOutputAzure";

const CopyIcon = () => (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.copyIcon}>
        <path d="M8 8.5h8.2A1.8 1.8 0 0 1 18 10.3v8A1.8 1.8 0 0 1 16.2 20h-8A1.8 1.8 0 0 1 6.4 18.2v-8A1.8 1.8 0 0 1 8 8.5Z" />
        <path d="M10 5h6.2A2.8 2.8 0 0 1 19 7.8V14" />
    </svg>
);

const CheckIcon = () => (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.copyIcon}>
        <path d="m5 12.5 4.2 4.2L19 7" />
    </svg>
);

const removeCitationMarkup = (html: string) => {
    const tempElement = document.createElement("div");
    tempElement.innerHTML = html;
    tempElement.querySelectorAll(".citationBadgeContainer, .supContainer, sup").forEach(node => node.remove());
    return tempElement.innerHTML;
};

const getCleanCopyText = (answer: ChatAppResponse) => {
    return (
        (answer.message?.content || "")
            // Remove source/file references such as [file.pdf#page=31]
            .replace(/\s*\[[^\]]*(?:\.pdf|\.docx|\.txt|\.md|#page=|https?:\/\/)[^\]]*\]/gi, "")
            // Remove numeric citation markers such as [1], [2], [3]
            .replace(/\s*\[\d+\]/g, "")
            // Remove generated Citation section if it exists
            .replace(/\n?\s*Citation:\s*[\s\S]*$/i, "")
            .replace(/\n{3,}/g, "\n\n")
            .trim()
    );
};

const copyTextToClipboard = async (text: string) => {
    try {
        if (navigator.clipboard?.writeText && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return true;
        }
    } catch {
        // Use fallback copy below
    }

    try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.setAttribute("readonly", "");
        textArea.style.position = "fixed";
        textArea.style.top = "0";
        textArea.style.left = "-9999px";
        textArea.style.opacity = "0";

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        textArea.setSelectionRange(0, textArea.value.length);

        const successful = document.execCommand("copy");
        document.body.removeChild(textArea);

        return successful;
    } catch (err) {
        console.error("Fallback copy failed:", err);
        return false;
    }
};

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
    onFollowupQuestionClicked,
    showFollowupQuestions,
    showSpeechOutputAzure,
    showSpeechOutputBrowser
}: Props) => {
    const followupQuestions = answer.context?.followup_questions;
    const parsedAnswer = useMemo(() => parseAnswerToHtml(answer, isStreaming, onCitationClicked), [answer, isStreaming, onCitationClicked]);

    const { t } = useTranslation();
    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);
    const displayAnswerHtml = useMemo(() => removeCitationMarkup(sanitizedAnswerHtml), [sanitizedAnswerHtml]);
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        const textToCopy = getCleanCopyText(answer);

        if (!textToCopy) {
            return;
        }

        const copiedSuccessfully = await copyTextToClipboard(textToCopy);

        if (copiedSuccessfully) {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } else {
            console.error("Failed to copy text");
        }
    };

    return (
        <Stack className={`${styles.answerContainer} ${isSelected && styles.selected}`} verticalAlign="space-between">
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    <AnswerIcon />
                    <div>
                        <button
                            type="button"
                            className={styles.copyButton}
                            title={copied ? t("tooltips.copied") : t("tooltips.copy")}
                            aria-label={copied ? t("tooltips.copied") : t("tooltips.copy")}
                            onClick={handleCopy}
                        >
                            {copied ? <CheckIcon /> : <CopyIcon />}
                        </button>

                        {showSpeechOutputAzure && (
                            <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                        )}

                        {showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                    </div>
                </Stack>
            </Stack.Item>

            <Stack.Item grow>
                <div className={styles.answerText}>
                    <ReactMarkdown children={displayAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                </div>
            </Stack.Item>

            {!!followupQuestions?.length && showFollowupQuestions && onFollowupQuestionClicked && (
                <Stack.Item>
                    <Stack horizontal wrap className={`${false ? styles.followupQuestionsList : ""}`} tokens={{ childrenGap: 6 }}>
                        <span className={styles.followupQuestionLearnMore}>{t("followupQuestions")}</span>
                        {followupQuestions.map((x, i) => (
                            <a key={i} className={styles.followupQuestion} title={x} onClick={() => onFollowupQuestionClicked(x)}>
                                {x}
                            </a>
                        ))}
                    </Stack>
                </Stack.Item>
            )}
        </Stack>
    );
};
