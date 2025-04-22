import React from "react";
import styles from "./AnalysisPanel.module.css";

interface ReflectionProps {
    next_answer: string | undefined;
    next_query: string | undefined;
}

export const Reflection: React.FC<ReflectionProps> = ({ next_answer, next_query }) => {
    return (
        <div className={styles.evaluationContainer}>
            <div className={styles.evaluationLabel}>Next Steps</div>
            <ul className={styles.evaluationList}>
                <li>Next Query: {next_query}</li>
                <li>Revised Answer: {next_answer}</li>
            </ul>
        </div>
    );
};
