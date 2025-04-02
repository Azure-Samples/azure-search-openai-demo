import React from "react";
import styles from "./AnalysisPanel.module.css";

export interface TokenUsage {
    prompt_tokens: number;
    completion_tokens: number;
    reasoning_tokens: number;
    total_tokens: number;
}

interface TokenUsageGraphProps {
    tokenUsage: TokenUsage;
    reasoningEffort?: string;
}

export const TokenUsageGraph: React.FC<TokenUsageGraphProps> = ({ tokenUsage, reasoningEffort }) => {
    const { prompt_tokens, completion_tokens, reasoning_tokens, total_tokens } = tokenUsage;

    // Calculate percentage widths relative to total_tokens
    const calcPercent = (value: number) => (total_tokens ? (value / total_tokens) * 100 : 0) + "%";

    return (
        <div className={styles.tokenUsageGraph}>
            <div className={styles.header}>Token Usage</div>
            <div className={styles.primaryBarContainer} style={{ width: "100%" }}>
                <div className={`${styles.tokenBar} ${styles.promptBar}`} style={{ width: calcPercent(prompt_tokens) }}>
                    <span className={styles.tokenLabel}>Prompt: {prompt_tokens}</span>
                </div>
                {reasoningEffort != null && reasoningEffort !== "" && (
                    <div className={`${styles.tokenBar} ${styles.reasoningBar}`} style={{ width: calcPercent(reasoning_tokens) }}>
                        <span className={styles.tokenLabel}>Reasoning: {reasoning_tokens}</span>
                    </div>
                )}
                <div className={`${styles.tokenBar} ${styles.outputBar}`} style={{ width: calcPercent(completion_tokens - reasoning_tokens) }}>
                    <span className={styles.tokenLabel}>Output: {completion_tokens - reasoning_tokens}</span>
                </div>
            </div>

            <div className={`${styles.tokenBar} ${styles.totalBar}`} style={{ width: calcPercent(total_tokens) }}>
                <span className={styles.tokenLabel}>Total: {total_tokens}</span>
            </div>
        </div>
    );
};
