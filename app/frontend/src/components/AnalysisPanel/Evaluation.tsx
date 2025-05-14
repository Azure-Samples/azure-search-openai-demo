import React from "react";
import styles from "./AnalysisPanel.module.css";

interface EvaluationProps {
    label: string;
    value: {
        thought_chain: string;
        score: number;
        explanation: string;
    };
}

export const Evaluation: React.FC<EvaluationProps> = ({ label, value }) => {
    return (
        <div className={styles.evaluationContainer}>
            <div className={styles.evaluationLabel}>{label}</div>
            <ul className={styles.evaluationList}>
                <li>Thought Chain: {value.thought_chain}</li>
                <li>Score: {value.score}</li>
                <li>Explanation: {value.explanation}</li>
            </ul>
        </div>
    );
};
