import { useState, useEffect } from "react";
import { IconButton } from "@fluentui/react";
import DOMPurify from "dompurify";
import { useMsal } from "@azure/msal-react";

import styles from "./FeedbackItem.module.css";

import { useLogin, getToken } from "../../authConfig";
import { ChatAppResponse, getCitationFilePath, getHeaders } from "../../api";
import { parseAnswerToHtml } from "../Answer/AnswerParser";
import { SupportingContent } from "../SupportingContent";
import { Icon } from "@fluentui/react/lib/Icon";

interface Props {
    id: string;
    feedback: string;
    question: string;
    answer: ChatAppResponse;
    comment: string;
    removeActiveSample: () => void;
}

const FeedbackItemDetailed = ({ id, feedback, question, answer, comment, removeActiveSample }: Props) => {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [activeCitation, setActiveCitation] = useState<string>("");
    const [citation, setCitation] = useState("");

    const choice = answer.choices[0];
    const index: number = choice.index;
    const message: string = choice.message.content;
    const context: string[] = choice.context.data_points;
    const session_state: any = choice.session_state;

    const parsedAnswer = parseAnswerToHtml(message, false, () => {});
    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);

    const client = useLogin ? useMsal().instance : undefined;

    const fetchCitation = async () => {
        const token = client ? await getToken(client) : undefined;

        if (activeCitation) {
            setIsLoading(true);
            const page = activeCitation.split("#")[1];
            // Get the end of the string starting from "#"
            const response = await fetch(activeCitation, {
                method: "GET",
                headers: getHeaders(token)
            });
            const citationContent = await response.blob();
            var citationObjectUrl;
            if (page !== "page=1") {
                citationObjectUrl = URL.createObjectURL(citationContent) + "#" + page;
            } else {
                citationObjectUrl = URL.createObjectURL(citationContent) + "#" + "page=2";
            }
            setCitation(citationObjectUrl);
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchCitation();
    }, [activeCitation]);

    return (
        <section className={[styles.feedbackItemContainer, feedback === "good" ? styles.feedbackGood : styles.feedbackBad].join(" ")}>
            <IconButton
                style={{ color: "black" }}
                iconProps={{ iconName: "ChevronLeftMed" }}
                title="Back to overview"
                ariaLabel="Back to overview"
                disabled={!answer.choices[0].context.data_points}
                onClick={() => removeActiveSample()}
            />
            <div className={styles.feedbackItem}>
                <span>Comment</span>
                <p>{comment}</p>
                <span>Question</span>
                <p>{question}</p>
                <span>Answer</span>
                <p className={styles.answerText} dangerouslySetInnerHTML={{ __html: sanitizedAnswerHtml }}></p>

                <span>Citations</span>
                <p>
                    {!!parsedAnswer.citations.length &&
                        parsedAnswer.citations.map((x, i) => {
                            const path = getCitationFilePath(x);
                            return (
                                <a key={i} className={styles.citation} title={x} onClick={() => setActiveCitation(path)}>
                                    {`${++i}. ${x}`}
                                </a>
                            );
                        })}
                </p>

                {/* <h3>{context}</h3> */}
                {/* <span>Context</span>
                <SupportingContent supportingContent={context} /> */}
            </div>
            {activeCitation &&
                (isLoading ? (
                    <p>Fetching Citation...</p>
                ) : (
                    <div className={styles.citationContainer}>
                        {activeCitation?.endsWith(".png") ? (
                            <img src={citation} className={styles.citationImg} />
                        ) : (
                            <iframe title="Citation" src={citation} width="100%" height="960px" />
                        )}
                    </div>
                ))}
        </section>
    );
};
export default FeedbackItemDetailed;
