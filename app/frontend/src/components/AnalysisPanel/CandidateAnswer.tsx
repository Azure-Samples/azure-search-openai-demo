import React from "react";
import styles from "./AnalysisPanel.module.css";

interface CandidateAnswerProps {
    candidate_answer: string | undefined;
}

export const CandidateAnswer: React.FC<CandidateAnswerProps> = ({ candidate_answer }) => {
    return (
        <div className={styles.evaluationContainer}>
            <div className={styles.evaluationLabel}>Candidate Answer</div>
            {candidate_answer ? (
                <div className={styles.answerText}>{candidate_answer}</div>
            ) : (
                <div className={styles.answerText}>No candidate answer available</div>
            )}
        </div>
    );
};
