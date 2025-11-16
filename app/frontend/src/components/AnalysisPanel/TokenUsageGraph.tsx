import React from "react";
import styles from "./AnalysisPanel.module.css";

export interface TokenUsage {
    prompt_tokens: number;
    completion_tokens: number;
    reasoning_tokens: number;
    total_tokens: number;
}

type TokenLabelKey = "prompt" | "reasoning" | "output" | "total";

type AdditionalTotal = {
    label: string;
    value: number;
    total?: number;
};

type SupplementaryUsage = {
    tokenUsage: TokenUsage;
    labels?: Partial<Record<TokenLabelKey, string>>;
    totalLabel?: string;
};

interface TokenUsageGraphProps {
    tokenUsage: TokenUsage;
    reasoningEffort?: string;
    title?: string;
    variant?: "full" | "totalOnly";
    totalLabel?: string;
    labels?: Partial<Record<TokenLabelKey, string>>;
    additionalTotals?: AdditionalTotal[];
    supplementaryUsages?: SupplementaryUsage[];
}

export const TokenUsageGraph: React.FC<TokenUsageGraphProps> = ({
    tokenUsage,
    reasoningEffort,
    title = "Token usage",
    variant = "full",
    totalLabel = "Total",
    labels,
    additionalTotals,
    supplementaryUsages
}) => {
    const { prompt_tokens, completion_tokens, reasoning_tokens, total_tokens } = tokenUsage;

    const calcPercent = (value: number, base: number = total_tokens) => {
        if (!base) {
            return "0%";
        }
        const percent = Math.min((value / base) * 100, 100);
        return `${percent}%`;
    };
    const showPrimaryBars = variant !== "totalOnly";
    const promptLabel = labels?.prompt ?? "Prompt";
    const reasoningLabel = labels?.reasoning ?? "Reasoning";
    const outputLabel = labels?.output ?? "Output";
    const resolvedTotalLabel = labels?.total ?? totalLabel;
    const supplementary = supplementaryUsages ?? [];

    const renderSegmentBars = (usage: TokenUsage, segmentLabels: { prompt: string; reasoning: string; output: string }, includeReasoning: boolean) => {
        const segmentTotal = usage.total_tokens;
        const reasoningValue = includeReasoning ? usage.reasoning_tokens : 0;
        const outputValue = usage.completion_tokens - reasoningValue;
        const safeOutputValue = Math.max(outputValue, 0);

        return (
            <div className={styles.primaryBarContainer} style={{ width: "100%" }}>
                <div className={`${styles.tokenBar} ${styles.promptBar}`} style={{ width: calcPercent(usage.prompt_tokens, segmentTotal) }}>
                    <span className={styles.tokenLabel}>
                        {segmentLabels.prompt}: {usage.prompt_tokens}
                    </span>
                </div>
                {includeReasoning && (
                    <div className={`${styles.tokenBar} ${styles.reasoningBar}`} style={{ width: calcPercent(reasoningValue, segmentTotal) }}>
                        <span className={styles.tokenLabel}>
                            {segmentLabels.reasoning}: {reasoningValue}
                        </span>
                    </div>
                )}
                <div className={`${styles.tokenBar} ${styles.outputBar}`} style={{ width: calcPercent(safeOutputValue, segmentTotal) }}>
                    <span className={styles.tokenLabel}>
                        {segmentLabels.output}: {safeOutputValue}
                    </span>
                </div>
            </div>
        );
    };

    const mainTotalClass = `${styles.tokenBar} ${styles.totalBar} ${showPrimaryBars ? styles.groupedTotalBar : styles.standaloneTotalBar}`;
    const mainTotal = (
        <div className={mainTotalClass} style={{ width: calcPercent(total_tokens) }}>
            <span className={styles.tokenLabel}>
                {resolvedTotalLabel}: {total_tokens}
            </span>
        </div>
    );

    return (
        <div className={styles.tokenUsageGraph}>
            {title && <div className={styles.header}>{title}</div>}
            {showPrimaryBars ? (
                <div className={`${styles.segmentWrapper} ${styles.segmentWrapperFirst}`}>
                    {renderSegmentBars(
                        tokenUsage,
                        {
                            prompt: promptLabel,
                            reasoning: reasoningLabel,
                            output: outputLabel
                        },
                        reasoningEffort != null && reasoningEffort !== ""
                    )}
                    {mainTotal}
                </div>
            ) : (
                mainTotal
            )}
            {additionalTotals?.map(extra => (
                <div
                    key={extra.label}
                    className={`${styles.tokenBar} ${styles.secondaryTotalBar} ${styles.standaloneTotalBar}`}
                    style={{ width: calcPercent(extra.value, extra.total ?? total_tokens) }}
                >
                    <span className={styles.tokenLabel}>
                        {extra.label}: {extra.value}
                    </span>
                </div>
            ))}
            {supplementary.map((segment, index) => (
                <div key={`${segment.totalLabel ?? "supplementary"}-${index}`} className={styles.segmentWrapper}>
                    {showPrimaryBars &&
                        renderSegmentBars(
                            segment.tokenUsage,
                            {
                                prompt: segment.labels?.prompt ?? "Prompt",
                                reasoning: segment.labels?.reasoning ?? "Reasoning",
                                output: segment.labels?.output ?? "Output"
                            },
                            false
                        )}
                    <div
                        className={`${styles.tokenBar} ${styles.secondaryTotalBar} ${showPrimaryBars ? styles.groupedTotalBar : styles.standaloneTotalBar}`}
                        style={{ width: calcPercent(segment.tokenUsage.total_tokens, segment.tokenUsage.total_tokens || 1) }}
                    >
                        <span className={styles.tokenLabel}>{`${
                            segment.labels?.total ?? segment.totalLabel ?? resolvedTotalLabel
                        }: ${segment.tokenUsage.total_tokens}`}</span>
                    </div>
                </div>
            ))}
        </div>
    );
};
