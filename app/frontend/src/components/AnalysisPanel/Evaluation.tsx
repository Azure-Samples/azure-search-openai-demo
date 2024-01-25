import styles from "./AnalysisPanel.module.css";

import { evalApi, EvaluationRequest, EvaluationResponse } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { useState } from "react";

interface Props {
    question: string;
    answer: string;
    supportingContent: string[];
}

interface SupportingItemProps {
    title: string;
    content: string;
}

const response: EvaluationResponse = {
    contextPrecision: 0.1,
    answerRelevance: 0.2,
    faithfulness: 0.3
};

const client = useLogin ? useMsal().instance : undefined;

export const Evaluation = ({ question, answer, supportingContent }: Props) => {
    const [evalResult, setEvalResult] = useState<EvaluationResponse | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

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
        } finally {
            setIsLoading(false);
        }
    };

    console.log("Eval", evalResult);

    return (
        <div className="">
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
            <div className="">
                {evalResult ? (
                    <>
                        <div>
                            <span>
                                <h2>Evaluation</h2>
                            </span>
                            <ul>
                                <li>Context Precision: {evalResult.contextPrecision}</li>
                                <li>Answer Relevance: {evalResult.answerRelevance}</li>
                                <li>Faithfulness: {evalResult.faithfulness}</li>
                            </ul>
                        </div>
                    </>
                ) : isLoading ? (
                    <>
                        <h3>Evaluating Answer...</h3>
                    </>
                ) : (
                    <button
                        style={{
                            margin: "2em auto",
                            display: "block",
                            fontSize: "17px",
                            padding: "0.5em 2em",
                            border: "transparent",
                            boxShadow: "2px 2px 4px rgba(0,0,0,0.4)",
                            background: "dodgerblue",
                            color: "white",
                            borderRadius: "4px"
                        }}
                        onClick={() => getEvaluation(question, supportingContent, answer)}
                    >
                        Evaluate
                    </button>
                )}
            </div>
        </div>
    );
};

export const TextSupportingContent = ({ title, content }: SupportingItemProps) => {
    return (
        <li className={styles.supportingContentItem}>
            <h4 className={styles.supportingContentItemHeader}>{title}</h4>
            <p className={styles.supportingContentItemText} dangerouslySetInnerHTML={{ __html: content }} />
        </li>
    );
};
