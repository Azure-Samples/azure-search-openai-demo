import React, { useMemo, useState } from "react";
import { Stack, IconButton } from "@fluentui/react";
import { useTranslation } from "react-i18next";
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
    // onThoughtProcessClicked: () => void;
    onSupportingContentClicked: () => void;
    onFollowupQuestionClicked?: (question: string) => void;
    showFollowupQuestions?: boolean;
    showSpeechOutputBrowser?: boolean;
    showSpeechOutputAzure?: boolean;
    workflowStateNo: number;
}

export const Answer = ({
    answer,
    index,
    speechConfig,
    isSelected,
    isStreaming,
    onCitationClicked,
    // onThoughtProcessClicked,
    onSupportingContentClicked,
    onFollowupQuestionClicked,
    showFollowupQuestions,
    showSpeechOutputAzure,
    showSpeechOutputBrowser,
    workflowStateNo
}: Props) => {
    const followupQuestions = answer.context?.followup_questions;
    const messageContent = answer.message.content;
    const parsedAnswer = useMemo(() => parseAnswerToHtml(messageContent, isStreaming, onCitationClicked), [answer]);
    const { t } = useTranslation();
    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);

    return (
        <Stack className={`${styles.answerContainer} ${isSelected && styles.selected}`} verticalAlign="space-between">
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    {workflowStateNo >= 1 && workflowStateNo <= 3 && <h1>Multi-Choice Questions</h1>}
                    {workflowStateNo >= 4 && workflowStateNo <= 7 && <h1>Open-Ended Questions</h1>}
                    {workflowStateNo >= 8 && workflowStateNo <= 9 && <h1>Exercises</h1>}
                </Stack>
            </Stack.Item>
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    <AnswerIcon />
                    <div>
                        {/* <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "Lightbulb" }}
                            title={t("tooltips.showThoughtProcess")}
                            ariaLabel={t("tooltips.showThoughtProcess")}
                            onClick={() => onThoughtProcessClicked()}
                            disabled={!answer.context.thoughts?.length}
                        /> */}
                        <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "ClipboardList" }}
                            title={t("tooltips.showSupportingContent")}
                            ariaLabel={t("tooltips.showSupportingContent")}
                            onClick={() => onSupportingContentClicked()}
                            disabled={!answer.context.data_points}
                        />

                        {workflowStateNo === 1 && (
                            <div>
                                <form onSubmit={event => event.preventDefault()}>
                                    <p>
                                        QUESTION 1. <strong>Which of the following is considered a risk-free interest rate?</strong>
                                    </p>
                                    <div>
                                        <input type="radio" id="libor" name="riskFreeRate" value="LIBOR" />
                                        <label htmlFor="libor">A. LIBOR</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="repoRate" name="riskFreeRate" value="Repo rate" />
                                        <label htmlFor="repoRate">B. Repo rate</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="treasuryRate" name="riskFreeRate" value="Treasury rate" />
                                        <label htmlFor="treasuryRate">C. Treasury rate</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="fedFundsRate" name="riskFreeRate" value="Fed funds rate" />
                                        <label htmlFor="fedFundsRate">D. Fed funds rate</label>
                                    </div>
                                </form>
                                <div></div>
                            </div>
                        )}

                        {workflowStateNo === 2 && (
                            <div>
                                <p>
                                    <strong>Correct answer:</strong> C
                                </p>
                                <form onSubmit={event => event.preventDefault()}>
                                    <p>
                                        QUESTION 2. <strong>What does the term LIBOR stand for?</strong>
                                    </p>
                                    <div>
                                        <input type="radio" id="liborA" name="liborMeaning" value="London Interbank Offered Rate" />
                                        <label htmlFor="liborA">A. London Interbank Offered Rate</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="liborB" name="liborMeaning" value="London Investment Bank Operational Rate" />
                                        <label htmlFor="liborB">B. London Investment Bank Operational Rate</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="liborC" name="liborMeaning" value="Low-Interest Bond Offer Rate" />
                                        <label htmlFor="liborC">C. Low-Interest Bond Offer Rate</label>
                                    </div>
                                </form>
                            </div>
                        )}

                        {workflowStateNo === 3 && (
                            <div>
                                <p>
                                    <strong>Correct answer:</strong> A
                                </p>
                                <p>
                                    QUESTION 3.
                                    <strong>
                                        When a bank states that the interest rate on one-year deposits is 10% per annum with annual compounding, how much will
                                        $100 grow to at the end of one year?
                                    </strong>
                                </p>
                                <form onSubmit={event => event.preventDefault()}>
                                    <div>
                                        <input type="radio" id="q3A" name="q3" value="$105" />
                                        <label htmlFor="q3A">A. $105</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="q3B" name="q3" value="$110" />
                                        <label htmlFor="q3B">B. $110</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="q3C" name="q3" value="$110.25" />
                                        <label htmlFor="q3C">C. $110.25</label>
                                    </div>
                                    <div>
                                        <input type="radio" id="q3D" name="q3" value="$110.38" />
                                        <label htmlFor="q3D">D. $110.38</label>
                                    </div>
                                </form>
                            </div>
                        )}
                        {workflowStateNo === 4 && (
                            <div>
                                <p>
                                    <strong>Correct answer:</strong> C
                                </p>
                                <p>
                                    Let's move to <strong>open-ended questions</strong>, shall we? For example:
                                </p>
                                <div>
                                    <div className={styles.answerText}>
                                        <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                                    </div>
                                </div>
                            </div>
                        )}
                        {workflowStateNo === 5 && (
                            <div>
                                {showSpeechOutputAzure && (
                                    <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                                )}
                                {showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                                <div className={styles.answerText}>
                                    <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                                </div>
                            </div>
                        )}
                        {workflowStateNo === 6 && (
                            <div>
                                {showSpeechOutputAzure && (
                                    <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                                )}
                                {showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                                <div className={styles.answerText}>
                                    <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                                </div>
                            </div>
                        )}
                        {workflowStateNo === 7 && (
                            <div>
                                {showSpeechOutputAzure && (
                                    <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                                )}
                                {showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                                <div className={styles.answerText}>
                                    <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                                </div>
                            </div>
                        )}
                        {workflowStateNo === 8 && (
                            <div>
                                <p>
                                    Good, let's do some <strong>quantitative exercises:</strong>
                                </p>
                                <div>
                                    Exercise 11 - A deposit account pays 12% per annum with continuous compounding, but interest is actually paid quarterly. How
                                    much interest will be paid each quarter on a $10,000 deposit?{" "}
                                </div>
                                {false && (
                                    <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                                )}
                                {false && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                            </div>
                        )}
                        {workflowStateNo === 9 && (
                            <div>
                                <p>
                                    Your answer is: <strong>CORRECT:</strong>
                                </p>
                                <div>
                                    <div>
                                        <p>SOLUTION</p>
                                        <p>
                                            To find how much interest will be paid each quarter on a $10,000 deposit, given a 12% annual interest rate with
                                            continuous compounding, we will follow these steps:
                                        </p>
                                        <p>
                                            <strong>Step 1: Use the formula for continuous compounding</strong>
                                        </p>
                                        <p>The formula for the balance after time \( t \) with continuous compounding is:</p>
                                        <p>A = P * e^(rt)</p>
                                        <p>
                                            Where:
                                            <br />
                                            - \( A \) is the amount after time \( t \),
                                            <br />
                                            - \( P \) is the principal (initial amount),
                                            <br />
                                            - \( r \) is the annual interest rate,
                                            <br />
                                            - \( t \) is the time in years,
                                            <br />- \( e \) is Euler’s number (approximately 2.71828).
                                        </p>
                                        <p>
                                            <strong>Step 2: Break the year into quarters</strong>
                                            <br />
                                            Since interest is paid quarterly, we calculate the interest for each quarter. Each quarter is \( \frac{1}
                                            {4} \) of a year, so:
                                        </p>
                                        <p>
                                            t = \( \frac{1}
                                            {4} \)
                                        </p>
                                        <p>The rate \( r = 0.12 \) (since 12% is expressed as 0.12 in decimal form).</p>
                                        <p>
                                            <strong>Step 3: Calculate the amount after one quarter</strong>
                                            <br />
                                            Using the formula:
                                        </p>
                                        <p>
                                            A = 10,000 * e^(0.12 * \( \frac{1}
                                            {4} \))
                                        </p>
                                        <p>We can now calculate this value.</p>
                                        <p>
                                            After one quarter, the total amount will be approximately $10,304.55.
                                            <br />
                                            The interest earned for the quarter is approximately $304.55 on the $10,000 deposit.
                                        </p>
                                        <p>
                                            <strong>Python Code</strong>
                                        </p>
                                        <pre>
                                            <code>
                                                {`import math

# Given values
P = 10000  # Principal amount
r = 0.12   # Annual interest rate (12%)
t = 1/4    # One quarter of a year

# Calculate the amount after one quarter with continuous compounding
A = P * math.exp(r * t)
A, A - P  # Return total amount and the interest earned`}
                                            </code>
                                        </pre>
                                        <strong>
                                            Excellent session, Nicolas! You have successfully completed the last part of the session; the quantitative
                                            exercises.
                                            <br />
                                            See you next time!
                                        </strong>
                                    </div>
                                </div>
                                {false && (
                                    <SpeechOutputAzure answer={sanitizedAnswerHtml} index={index} speechConfig={speechConfig} isStreaming={isStreaming} />
                                )}
                                {false && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                            </div>
                        )}
                    </div>
                </Stack>
            </Stack.Item>

            <Stack.Item grow>
                {/* <div className={styles.answerText}>
                    <ReactMarkdown children={sanitizedAnswerHtml} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]} />
                </div> */}
            </Stack.Item>

            {!!parsedAnswer.citations.length && (
                <Stack.Item>
                    <Stack horizontal wrap tokens={{ childrenGap: 5 }}>
                        <span className={styles.citationLearnMore}>{t("citationWithColon")}</span>
                        {parsedAnswer.citations.map((x, i) => {
                            const path = getCitationFilePath(x);
                            return (
                                <a key={i} className={styles.citation} title={x} onClick={() => onCitationClicked(path)}>
                                    {`${++i}. ${x}`}
                                </a>
                            );
                        })}
                    </Stack>
                </Stack.Item>
            )}

            {!!followupQuestions?.length && showFollowupQuestions && onFollowupQuestionClicked && (
                <Stack.Item>
                    <Stack horizontal wrap className={`${!!parsedAnswer.citations.length ? styles.followupQuestionsList : ""}`} tokens={{ childrenGap: 6 }}>
                        <span className={styles.followupQuestionLearnMore}>{t("followupQuestions")}</span>
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
        </Stack>
    );
};
