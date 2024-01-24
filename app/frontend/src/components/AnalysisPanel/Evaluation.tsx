import { parseSupportingContentItem } from "../SupportingContent/SupportingContentParser";

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

/*
Evaluations that we can do:
- Context Precision: Question & Context
- Answer Relevance: Question & Answer
- Faithfulness: Answer & Context
*/

const response: EvaluationResponse = {
    contextPrecision: 0.1,
    answerRelevance: 0.2,
    faithfulness: 0.3
};

const client = useLogin ? useMsal().instance : undefined;

export const Evaluation = ({ question, answer, supportingContent }: Props) => {
    const [evalResult, setEvalResult] = useState<EvaluationResponse | null>(null);

    const getEvaluation = async (question: string, contexts: string[], answer: string) => {
        // const token = client ? await getToken(client) : undefined;
        // const request: EvaluationRequest = {
        //     question: question,
        //     contexts: contexts,
        //     answer: answer
        // };
        // const response: EvaluationResponse = await evalApi(request, token);
        setEvalResult(response);
        // console.log(response);
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
                {evalResult === null ? (
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
                ) : (
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
                )}
            </div>
        </div>
    );
};

// export const EvaluationResult = (contextPrecision: number, answerRelevance: number, faithfulness: number) => {
//     return (
//         <ul>
//             <li>Context Precision: {contextPrecision}</li>
//             <li>Answer Relevance: {answerRelevance}</li>
//             <li>Faithfulness: {faithfulness}</li>
//         </ul>
//     );
// };

// export const EvalButton = ({ question, supportingContent, answer, getEvaluation }: Props) => {
//     return (
//         <button
//             className="eval_button"
//             style={{
//                 margin: "2em auto",
//                 display: "block",
//                 fontSize: "17px",
//                 padding: "0.5em 2em",
//                 border: "transparent",
//                 boxShadow: "2px 2px 4px rgba(0,0,0,0.4)",
//                 background: "dodgerblue",
//                 color: "white",
//                 borderRadius: "4px"
//             }}
//             onClick={() => getEvaluation(question, supportingContent, answer)}
//         >
//             Evaluate
//         </button>
//     );
// };

export const TextSupportingContent = ({ title, content }: SupportingItemProps) => {
    return (
        <li className={styles.supportingContentItem}>
            <h4 className={styles.supportingContentItemHeader}>{title}</h4>
            <p className={styles.supportingContentItemText} dangerouslySetInnerHTML={{ __html: content }} />
        </li>
    );
};
