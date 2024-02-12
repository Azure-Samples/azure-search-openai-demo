import { useState, useEffect } from "react";

import styles from "./EvalItem.module.css";
import { Stack, IconButton } from "@fluentui/react";
import DOMPurify from "dompurify";
import { useMsal } from "@azure/msal-react";

import { ChatAppResponse } from "../../api";
import { SupportingContent } from "../SupportingContent";
import { useLogin, getToken } from "../../authConfig";
import { parseSupportingContentItem } from "../SupportingContent/SupportingContentParser";
import { parseAnswerToHtml } from "../Answer/AnswerParser";
import { getCitationFilePath, getHeaders } from "../../api";

interface Props {
    question: string;
    answer: string;
    context: string;
    relevance: number;
    coherence: number;
    similarity: number;
    groundedness: number;
    removeActiveSample: () => void;
}

const EvalItemDetailed = ({ question, answer, context, relevance, coherence, similarity, groundedness, removeActiveSample }: Props) => {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [activeCitation, setActiveCitation] = useState<string>("");
    const [citation, setCitation] = useState("");

    const parsedAnswer = parseAnswerToHtml(answer, false, () => {});
    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);
    const citations: string[] = parsedAnswer.citations;

    const parsedContext = parseSupportingContentItem(context);

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
        <section className={styles.evalItemContainer}>
            <IconButton
                style={{ color: "black" }}
                iconProps={{ iconName: "ChevronLeftMed" }}
                title="Back to overview"
                ariaLabel="Back to overview"
                onClick={() => removeActiveSample()}
            />
            <div className={styles.evalItemDetailed}>
                <div className={styles.metricsDetailedContainer}>
                    <div className={styles.metricGridElem}>
                        <span>Groundedness</span>
                        {groundedness}
                    </div>
                    <div className={styles.metricGridElem}>
                        <span>Relevance</span>
                        {relevance}
                    </div>
                    <div className={styles.metricGridElem}>
                        <span>Coherence</span>
                        {coherence}
                    </div>
                    <div className={styles.metricGridElem}>
                        <span>Similarity</span>
                        {similarity}
                    </div>
                </div>
                <div className={styles.evalItemDetailedTextContainer}>
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

                    {/* <span>Context</span>
                    <p>{context}</p> */}
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
            </div>
        </section>
    );
};
export default EvalItemDetailed;
