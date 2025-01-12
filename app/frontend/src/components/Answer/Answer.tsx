import { useMemo, useState, useEffect, useRef, useContext } from "react";
import { Stack, IconButton } from "@fluentui/react";
import { useTranslation } from "react-i18next";
import DOMPurify from "dompurify";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

import styles from "./Answer.module.css";
import { type ChatAppResponse, getCitationFilePath, type SpeechConfig } from "../../api";
import { parseAnswerToHtml } from "./AnswerParser";
import { AnswerIcon } from "./AnswerIcon";
import { SpeechOutputBrowser } from "./SpeechOutputBrowser";
import { SpeechOutputAzure } from "./SpeechOutputAzure";
import { useFeedback } from "./FeedbackContext";
import { useHistoryManager } from "../HistoryProviders/HistoryManager";
import { HistoryProviderOptions } from "../HistoryProviders/IProvider";
import { FeedbackStore } from "./FeedbackStore";
import { useLogin } from "../../authConfig";
import { LoginContext } from "../../loginContext";
import { FeedbackDialog } from "./FeedbackDialog";

interface Props {
    answer: ChatAppResponse;
    index: number;
    speechConfig: SpeechConfig;
    isSelected?: boolean;
    isStreaming: boolean;
    historyFeedback?: number;
    onCitationClicked: (filePath: string) => void;
    onThoughtProcessClicked: () => void;
    onSupportingContentClicked: () => void;
    onFollowupQuestionClicked?: (question: string) => void;
    showFollowupQuestions?: boolean;
    showSpeechOutputBrowser?: boolean;
    showSpeechOutputAzure?: boolean;
}

interface FeedbackData {
    store: FeedbackStore;
    traceId: string | undefined;
    historyValue: number | undefined;
}

// New custom hook for feedback state management
const useFeedbackState = (traceId: string | undefined, historyFeedback: number | undefined) => {
    const [feedbackValue, setFeedbackValue] = useState<number | null>(null);
    const initializeAttempted = useRef(false);
    const feedbackStore = useMemo(() => FeedbackStore.getInstance(), []);

    // Reset state when traceId changes
    useEffect(() => {
        setFeedbackValue(null);
        initializeAttempted.current = false;
    }, [traceId]);

    // Load feedback data with improved error handling
    useEffect(() => {
        const loadFeedback = async () => {
            if (!traceId || initializeAttempted.current) return;

            try {
                initializeAttempted.current = true;
                console.log(`Initializing feedback for trace ${traceId}`);

                const cachedValue = await feedbackStore.getFeedback(traceId);
                if (cachedValue !== null) {
                    console.log(`Found cached feedback for ${traceId}:`, cachedValue);
                    setFeedbackValue(cachedValue);
                    return;
                }

                if (historyFeedback !== undefined) {
                    console.log(`Using history feedback for ${traceId}:`, historyFeedback);
                    setFeedbackValue(historyFeedback);
                    await feedbackStore.setFeedback(traceId, historyFeedback);
                }
            } catch (error) {
                console.error(`Failed to load feedback for ${traceId}:`, error);
                initializeAttempted.current = false;
            }
        };

        loadFeedback();
    }, [traceId, historyFeedback, feedbackStore]);

    return { feedbackValue, setFeedbackValue, feedbackStore };
};

export const Answer = ({ answer, historyFeedback, ...props }: Props) => {
    const followupQuestions = answer.context?.followup_questions;
    const parsedAnswer = useMemo(
        () => parseAnswerToHtml(answer, props.isStreaming, props.onCitationClicked),
        [answer, props.isStreaming, props.onCitationClicked]
    );
    const { t } = useTranslation();
    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);
    const [copied, setCopied] = useState(false);
    const { feedbackState } = useFeedback();
    const historyManager = useHistoryManager(HistoryProviderOptions.IndexedDB);
    const traceId = answer.context?.trace_id;
    const { loggedIn } = useContext(LoginContext);
    const useAuth = useLogin && loggedIn;

    const answerContextValue = useMemo(
        () => ({
            fullContext: answer.context,
            traceId: answer.context?.trace_id,
            fullAnswer: answer,
            hasTrace: Boolean(answer.context?.trace_id),
            contextKeys: Object.keys(answer.context || {})
        }),
        [answer]
    );

    const feedback = useMemo<FeedbackData>(
        () => ({
            store: FeedbackStore.getInstance(),
            traceId: answer.context?.trace_id,
            historyValue: historyFeedback
        }),
        [answer.context?.trace_id, historyFeedback]
    );

    const { feedbackValue, setFeedbackValue, feedbackStore } = useFeedbackState(answer.context?.trace_id, historyFeedback);

    const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
    const [pendingFeedbackValue, setPendingFeedbackValue] = useState<number | null>(null);

    const handleCopy = () => {
        const textToCopy = sanitizedAnswerHtml.replace(/<a [^>]*><sup>\d+<\/sup><\/a>|<[^>]+>/g, "");

        navigator.clipboard
            .writeText(textToCopy)
            .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            })
            .catch(err => console.error("Failed to copy text: ", err));
    };

    // Enhanced error handling in feedback submission
    const handleFeedback = async (value: number) => {
        if (!feedback.traceId) return;
        setPendingFeedbackValue(value);
        setShowFeedbackDialog(true);
    };

    const handleFeedbackSubmit = async (comment: string) => {
        if (!feedback.traceId || pendingFeedbackValue === null) return;

        try {
            setFeedbackValue(pendingFeedbackValue);
            await feedbackStore.setFeedback(feedback.traceId, pendingFeedbackValue);

            try {
                const res = await fetch("/feedback", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        trace_id: feedback.traceId,
                        value: pendingFeedbackValue,
                        score: pendingFeedbackValue,
                        type: "user_feedback",
                        comment: comment || (pendingFeedbackValue === 1 ? "👍 Positive feedback" : "👎 Negative feedback")
                    })
                });

                const responseBody = await res.text();
                const isHtmlError = responseBody.trim().startsWith("<!doctype") || responseBody.trim().startsWith("<html");

                if (res.ok) {
                    console.log(`Server: Successfully sent feedback=${pendingFeedbackValue} for ${feedback.traceId}`);
                } else {
                    const errorDetails = isHtmlError ? `Received HTML error page (${res.status})` : `Response: ${responseBody}`;
                    console.warn(`Server: HTTP ${res.status} when sending feedback=${pendingFeedbackValue} for ${feedback.traceId}`, errorDetails);
                }
            } catch (error) {
                if (error instanceof TypeError || error instanceof SyntaxError) {
                    console.error(`Server: Network/parsing error sending feedback=${pendingFeedbackValue} for ${feedback.traceId}:`, error);
                } else {
                    console.warn(`Server: Failed to send feedback=${pendingFeedbackValue} for ${feedback.traceId}:`, error);
                }
            }

            // Update history store if authenticated
            if (useAuth) {
                await historyManager.updateFeedback(feedback.traceId, pendingFeedbackValue);
            }

            const storedValue = await feedbackStore.getFeedback(feedback.traceId);
            if (storedValue !== pendingFeedbackValue) {
                console.warn(`Local feedback verification failed: stored=${storedValue}, expected=${pendingFeedbackValue}`);
            }

            // Show success message with proper cleanup
            const feedbackMessage = document.createElement("div");
            feedbackMessage.className = styles.feedbackMessage;
            feedbackMessage.textContent = "Thanks for your feedback!";
            document.body.appendChild(feedbackMessage);
            setTimeout(() => feedbackMessage.remove(), 3000);
        } catch (error) {
            console.error(`Failed to store feedback for ${feedback.traceId}:`, error);

            // Show error message with proper cleanup
            const errorMessage = document.createElement("div");
            errorMessage.className = styles.errorMessage;
            errorMessage.textContent = error instanceof Error ? error.message : "Failed to submit feedback";
            document.body.appendChild(errorMessage);
            setTimeout(() => errorMessage.remove(), 3000);
        } finally {
            setShowFeedbackDialog(false);
            setPendingFeedbackValue(null);
        }
    };

    useEffect(() => {
        const isDevelopment = import.meta.env?.DEV ?? false;
        if (isDevelopment) {
            console.log("Answer mounted with context:", answerContextValue);
        }
    }, [answerContextValue]);

    const renderFeedbackButton = () => {
        if (feedbackValue !== null) {
            return (
                <IconButton
                    style={{ color: "black" }}
                    className={styles.feedbackButtonClicked}
                    iconProps={{ iconName: feedbackValue === 1 ? "LikeSolid" : "DislikeSolid" }}
                    title={feedbackValue === 1 ? t("Good response") : t("Bad response")}
                    disabled={true}
                />
            );
        }

        return (
            <>
                <IconButton
                    style={{ color: "black" }}
                    iconProps={{ iconName: "Like" }}
                    title={t("Good response")}
                    onClick={() => handleFeedback(1)}
                    disabled={!traceId || props.isStreaming}
                />
                <IconButton
                    style={{ color: "black" }}
                    iconProps={{ iconName: "Dislike" }}
                    title={t("Bad response")}
                    onClick={() => handleFeedback(0)}
                    disabled={!traceId || props.isStreaming}
                />
            </>
        );
    };

    return (
        <>
            <Stack className={`${styles.answerContainer} ${props.isSelected && styles.selected}`} verticalAlign="space-between">
                <Stack.Item>
                    <Stack horizontal horizontalAlign="space-between">
                        <AnswerIcon />
                        <div>
                            {renderFeedbackButton()}
                            <IconButton
                                style={{ color: "black" }}
                                iconProps={{ iconName: copied ? "CheckMark" : "Copy" }}
                                title={copied ? t("tooltips.copied") : t("tooltips.copy")}
                                ariaLabel={copied ? t("tooltips.copied") : t("tooltips.copy")}
                                onClick={handleCopy}
                            />
                            <IconButton
                                style={{ color: "black" }}
                                iconProps={{ iconName: "Lightbulb" }}
                                title={t("tooltips.showThoughtProcess")}
                                ariaLabel={t("tooltips.showThoughtProcess")}
                                onClick={() => props.onThoughtProcessClicked()}
                                disabled={!answer.context.thoughts?.length}
                            />
                            <IconButton
                                style={{ color: "black" }}
                                iconProps={{ iconName: "ClipboardList" }}
                                title={t("tooltips.showSupportingContent")}
                                ariaLabel={t("tooltips.showSupportingContent")}
                                onClick={() => props.onSupportingContentClicked()}
                                disabled={!answer.context.data_points}
                            />
                            {props.showSpeechOutputAzure && (
                                <SpeechOutputAzure
                                    answer={sanitizedAnswerHtml}
                                    index={props.index}
                                    speechConfig={props.speechConfig}
                                    isStreaming={props.isStreaming}
                                />
                            )}
                            {props.showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                        </div>
                    </Stack>
                </Stack.Item>

                <Stack.Item grow>
                    <div className={styles.answerText}>
                        <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                    </div>
                </Stack.Item>

                {!!parsedAnswer.citations.length && (
                    <Stack.Item>
                        <Stack horizontal wrap tokens={{ childrenGap: 5 }}>
                            <span className={styles.citationLearnMore}>{t("citationWithColon")}</span>
                            {parsedAnswer.citations.map((x, i) => {
                                const path = getCitationFilePath(x);
                                return (
                                    <a key={i} className={styles.citation} title={x} onClick={() => props.onCitationClicked(path)}>
                                        {`${++i}. ${x}`}
                                    </a>
                                );
                            })}
                        </Stack>
                    </Stack.Item>
                )}

                {!!followupQuestions?.length && props.showFollowupQuestions && props.onFollowupQuestionClicked && (
                    <Stack.Item>
                        <Stack horizontal wrap className={`${!!parsedAnswer.citations.length ? styles.followupQuestionsList : ""}`} tokens={{ childrenGap: 6 }}>
                            <span className={styles.followupQuestionLearnMore}>{t("followupQuestions")}</span>
                            {followupQuestions.map((x, i) => (
                                <a
                                    key={i}
                                    className={styles.followupQuestion}
                                    title={x}
                                    onClick={() => props.onFollowupQuestionClicked && props.onFollowupQuestionClicked(x)}
                                >
                                    {x}
                                </a>
                            ))}
                        </Stack>
                    </Stack.Item>
                )}
            </Stack>

            <FeedbackDialog
                isOpen={showFeedbackDialog}
                value={pendingFeedbackValue ?? 0}
                onDismiss={() => setShowFeedbackDialog(false)}
                onSubmit={handleFeedbackSubmit}
            />
        </>
    );
};
