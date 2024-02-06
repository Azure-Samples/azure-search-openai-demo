import { ChatAppResponse } from "../../api";
import styles from "./EvalItem.module.css";
import { IconButton } from "@fluentui/react";

interface Props {
    id: number;
    feedback: string;
    question: string;
    answer: string;
    relevance: number;
    coherence: number;
    similarity: number;
    groundedness: number;
}

const EvalItem = ({ id, question, answer, relevance, coherence, similarity, groundedness }: Props) => {
    return (
        <section className={styles.evalItemContainer}>
            <div className={styles.evalItem}>
                <div className={styles.questionContainer}>
                    <span>Question</span>
                    <p>{question}</p>
                    {/* <span>Answer</span>
                    <p>{answer}</p> */}
                </div>
                <div className={styles.metricsContainer}>
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
            </div>
        </section>
    );
};
export default EvalItem;
