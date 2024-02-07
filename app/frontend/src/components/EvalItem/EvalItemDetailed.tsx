import { ChatAppResponse } from "../../api";
import styles from "./EvalItem.module.css";
import { IconButton } from "@fluentui/react";
import { SupportingContent } from "../SupportingContent";

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
                    <p>{answer}</p>
                    <span>Context</span>
                    <p>{context}</p>
                </div>
            </div>
        </section>
    );
};
export default EvalItemDetailed;
