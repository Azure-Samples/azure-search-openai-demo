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
    tone?: TokenUsageValueBarTone;
};

type PercentBase = number | undefined;

const calcPercent = (value: number, base: PercentBase) => {
    if (!base) {
        return "0%";
    }
    const normalized = Math.max(value, 0);
    const percent = Math.min((normalized / base) * 100, 100);
    return `${percent}%`;
};

export interface TokenUsageSegmentLabels {
    prompt: string;
    output: string;
    reasoning?: string;
}

interface TokenUsageStackedBarProps {
    tokenUsage: TokenUsage;
    labels: TokenUsageSegmentLabels;
    includeReasoning?: boolean;
}

export const TokenUsageStackedBar: React.FC<TokenUsageStackedBarProps> = ({ tokenUsage, labels, includeReasoning = false }) => {
    const base = tokenUsage.total_tokens || 1;
    const reasoningValue = includeReasoning ? tokenUsage.reasoning_tokens : 0;
    const outputValue = tokenUsage.completion_tokens - reasoningValue;
    const safeOutputValue = Math.max(outputValue, 0);

    return (
        <div className={styles.primaryBarContainer}>
            <div className={`${styles.tokenBar} ${styles.promptBar}`} style={{ width: calcPercent(tokenUsage.prompt_tokens, base) }}>
                <span className={styles.tokenLabel}>
                    {labels.prompt}: {tokenUsage.prompt_tokens}
                </span>
            </div>
            {includeReasoning && (
                <div className={`${styles.tokenBar} ${styles.reasoningBar}`} style={{ width: calcPercent(reasoningValue, base) }}>
                    <span className={styles.tokenLabel}>
                        {labels.reasoning ?? "Reasoning"}: {reasoningValue}
                    </span>
                </div>
            )}
            <div className={`${styles.tokenBar} ${styles.outputBar}`} style={{ width: calcPercent(safeOutputValue, base) }}>
                <span className={styles.tokenLabel}>
                    {labels.output}: {safeOutputValue}
                </span>
            </div>
        </div>
    );
};

export type TokenUsageValueBarTone = "primary" | "secondary";
type TokenUsageValueBarGrouping = "grouped" | "standalone";

interface TokenUsageValueBarProps {
    label: string;
    value: number;
    base?: PercentBase;
    tone?: TokenUsageValueBarTone;
    grouping?: TokenUsageValueBarGrouping;
}

export const TokenUsageValueBar: React.FC<TokenUsageValueBarProps> = ({ label, value, base, tone = "primary", grouping = "standalone" }) => {
    const toneClass = tone === "primary" ? styles.totalBar : styles.secondaryTotalBar;
    const groupingClass = grouping === "grouped" ? styles.groupedTotalBar : styles.standaloneTotalBar;
    const resolvedBase = base ?? (value || 1);

    return (
        <div className={`${styles.tokenBar} ${toneClass} ${groupingClass}`} style={{ width: calcPercent(value, resolvedBase) }}>
            <span className={styles.tokenLabel}>
                {label}: {value}
            </span>
        </div>
    );
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
    const { total_tokens } = tokenUsage;
    const showPrimaryBars = variant !== "totalOnly";
    const promptLabel = labels?.prompt ?? "Prompt";
    const reasoningLabel = labels?.reasoning ?? "Reasoning";
    const outputLabel = labels?.output ?? "Output";
    const resolvedTotalLabel = labels?.total ?? totalLabel;
    const supplementary = supplementaryUsages ?? [];
    const includeReasoning = showPrimaryBars && Boolean(reasoningEffort) && tokenUsage.reasoning_tokens > 0;

    return (
        <div className={styles.tokenUsageGraph}>
            {title && <div className={styles.header}>{title}</div>}
            {showPrimaryBars ? (
                <div className={`${styles.segmentWrapper} ${styles.segmentWrapperFirst}`}>
                    <TokenUsageStackedBar
                        tokenUsage={tokenUsage}
                        labels={{ prompt: promptLabel, output: outputLabel, reasoning: reasoningLabel }}
                        includeReasoning={includeReasoning}
                    />
                    <TokenUsageValueBar label={resolvedTotalLabel} value={total_tokens} base={total_tokens} tone="primary" grouping="grouped" />
                </div>
            ) : (
                <TokenUsageValueBar label={resolvedTotalLabel} value={total_tokens} base={total_tokens} tone="primary" grouping="standalone" />
            )}
            {additionalTotals?.map(extra => (
                <TokenUsageValueBar
                    key={extra.label}
                    label={extra.label}
                    value={extra.value}
                    base={extra.total ?? total_tokens}
                    tone="secondary"
                    grouping="standalone"
                />
            ))}
            {supplementary.map((segment, index) => (
                <div key={`${segment.totalLabel ?? "supplementary"}-${index}`} className={styles.segmentWrapper}>
                    {showPrimaryBars && (
                        <TokenUsageStackedBar
                            tokenUsage={segment.tokenUsage}
                            labels={{
                                prompt: segment.labels?.prompt ?? "Prompt",
                                output: segment.labels?.output ?? "Output",
                                reasoning: segment.labels?.reasoning ?? "Reasoning"
                            }}
                            includeReasoning={false}
                        />
                    )}
                    <TokenUsageValueBar
                        label={segment.labels?.total ?? segment.totalLabel ?? resolvedTotalLabel}
                        value={segment.tokenUsage.total_tokens}
                        base={segment.tokenUsage.total_tokens || 1}
                        tone={segment.tone ?? "secondary"}
                        grouping={showPrimaryBars ? "grouped" : "standalone"}
                    />
                </div>
            ))}
        </div>
    );
};
