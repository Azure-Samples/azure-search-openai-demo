import { Stack } from "@fluentui/react";
import React from "react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";

import styles from "./AnalysisPanel.module.css";

import { Thoughts } from "../../api";
import { AgentPlan } from "./AgentPlan";
import { TokenUsageGraph } from "./TokenUsageGraph";

SyntaxHighlighter.registerLanguage("json", json);

interface Props {
    thoughts: Thoughts[];
    onCitationClicked?: (citationFilePath: string) => void;
}

// Helper to truncate URLs
function truncateImageUrl(val: string) {
    if (typeof val === "string" && val.startsWith("data:image/")) {
        return val.slice(0, 30) + "...";
    }
    return val;
}

export const ThoughtProcess = ({ thoughts, onCitationClicked }: Props) => {
    const [effort, setEffort] = React.useState<string | undefined>();

    return (
        <ul className={styles.tList}>
            {thoughts.map((t, ind) => {
                const hasAgenticPlan = Array.isArray(t.props?.query_plan) && t.props.query_plan.length > 0;
                return (
                    <li className={styles.tListItem} key={ind}>
                        <div className={styles.tStep}>{t.title}</div>
                        <Stack horizontal tokens={{ childrenGap: 5 }} className={styles.tPropRow}>
                            {t.props &&
                                (Object.keys(t.props).filter(k => k !== "token_usage" && k !== "query_plan") || []).map((k: any) => (
                                    <span className={styles.tProp} key={k}>
                                        {k}: {truncateImageUrl(JSON.stringify(t.props?.[k]))}
                                    </span>
                                ))}
                            {hasAgenticPlan && effort && <span className={styles.tProp}>effort: {effort}</span>}
                        </Stack>
                        {t.props?.token_usage && !hasAgenticPlan && (
                            <TokenUsageGraph tokenUsage={t.props.token_usage} reasoningEffort={t.props.reasoning_effort} />
                        )}
                        {hasAgenticPlan && (
                            <AgentPlan
                                queryPlan={t.props?.query_plan ?? []}
                                onEffortExtracted={setEffort}
                                onCitationClicked={onCitationClicked}
                                results={Array.isArray(t.description) ? t.description : []}
                            />
                        )}
                        {Array.isArray(t.description) || (t.description !== null && typeof t.description === "object") ? (
                            <SyntaxHighlighter language="json" wrapLines wrapLongLines className={styles.tCodeBlock} style={a11yLight}>
                                {JSON.stringify(t.description, (key, value) => truncateImageUrl(value), 2)}
                            </SyntaxHighlighter>
                        ) : (
                            <div>{t.description}</div>
                        )}
                    </li>
                );
            })}
        </ul>
    );
};
