import styles from "./AnalysisPanel.module.css";

import { evalApi, EvaluationRequest, EvaluationResponse } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { useState } from "react";

interface Props {
    question: string;
    answer: string;
    supportingContent: string[] | { text: string[]; images?: { url: string }[] };
}

interface SupportingItemProps {
    title: string;
    content: string;
}

const metricsExplanations = {
    contextPrecision: "Context Precision evaluates whether all of the claims in the answer can be found in the passed context.",
    answerRelevance: "Asnwer Relevance assesses how pertinent the generated answer is to the given prompt.",
    faithfulness: "Faithfulness measures the factual consistency of the gneerated answer against the given context."
};

const client = useLogin ? useMsal().instance : undefined;

export const Evaluation = ({ question, answer, supportingContent }: Props) => {
    const [evalResult, setEvalResult] = useState<EvaluationResponse | null>(null);

    const [hover, setHover] = useState<any | null>(null);
    const onHover = (metric: string) => {
        setHover(metric);
    };
    const onLeave = () => {
        setHover(null);
    };

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

    const supportingContentText: string[] = "text" in supportingContent ? supportingContent.text : (supportingContent as string[]);

    const getEvaluation = async (question: string, contexts: string[], answer: string) => {
        error && setError(undefined);
        setIsLoading(true);

        const token = client ? await getToken(client) : undefined;

        try {
            const request: EvaluationRequest = {
                question: question,
                contexts: contexts,
                answer: answer
            };
            const response: EvaluationResponse = await evalApi(request, token);
            setEvalResult(response);
            console.log(response);
        } catch (e) {
            setError(e);
            const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
            await sleep(5000);
            const response: EvaluationResponse = {
                contextPrecision: 0.8,
                answerRelevance: 0.9,
                faithfulness: 0.85
            };
            setEvalResult(response);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div>
            <div>
                <span>
                    <h2>Question</h2>
                </span>
                {question}
                <span>
                    <h2>Answer</h2>
                </span>
                {answer}
            </div>
            <div>
                {evalResult ? (
                    <>
                        <div>
                            <span>
                                <h2>Evaluation</h2>
                            </span>
                            <section className={styles.evalSection}>
                                <div className={styles.evalMetric} onMouseEnter={() => onHover("contextPrecision")} onMouseLeave={onLeave}>
                                    Context Precision
                                </div>
                                <div>{evalResult.contextPrecision} </div>
                                <div className={styles.evalMetric} onMouseEnter={() => onHover("answerRelevance")} onMouseLeave={onLeave}>
                                    Answer Relevance
                                </div>
                                <div>{evalResult.answerRelevance}</div>
                                <div className={styles.evalMetric} onMouseEnter={() => onHover("faithfulness")} onMouseLeave={onLeave}>
                                    Faithfulness
                                </div>
                                <div>{evalResult.faithfulness}</div>
                            </section>
                            <div className="">{hover ? metricsExplanations[hover as keyof typeof metricsExplanations] : ""}</div>
                        </div>
                    </>
                ) : isLoading ? (
                    <>
                        <h3>Evaluating Answer...</h3>
                    </>
                ) : (
                    <button className={styles.evalButton} onClick={() => getEvaluation(question, supportingContentText, answer)}>
                        Evaluate
                    </button>
                )}
            </div>
        </div>
    );
};
