import { Stack } from "@fluentui/react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";

import styles from "./AnalysisPanel.module.css";

import { Thoughts } from "../../api";
import { TokenUsageGraph } from "./TokenUsageGraph";
import { AgentPlan } from "./AgentPlan";
import { CitationDetail } from "../Answer/AnswerParser";

SyntaxHighlighter.registerLanguage("json", json);

interface Props {
    thoughts: Thoughts[];
    citationDetails?: CitationDetail[];
}

// Helper to truncate URLs
function truncateImageUrl(val: string) {
    if (typeof val === "string" && val.startsWith("data:image/")) {
        return val.slice(0, 30) + "...";
    }
    return val;
}

export const ThoughtProcess = ({ thoughts, citationDetails }: Props) => {
    return (
        <ul className={styles.tList}>
            {thoughts.map((t, ind) => {
                const hasAgenticPlan = Array.isArray(t.props?.query_plan) && t.props.query_plan.length > 0;
                return (
                    <li className={styles.tListItem} key={ind}>
                        <div className={styles.tStep}>{t.title}</div>
                        <Stack horizontal tokens={{ childrenGap: 5 }} className={styles.tPropRow}>
                            {t.props &&
                                (Object.keys(t.props).filter(k => k !== "token_usage" && k !== "query_plan" && k !== "citation_mapping") || []).map(
                                    (k: any) => (
                                        <span className={styles.tProp} key={k}>
                                            {k}: {truncateImageUrl(JSON.stringify(t.props?.[k]))}
                                        </span>
                                    )
                                )}
                        </Stack>
                        {t.props?.token_usage && !hasAgenticPlan && (
                            <TokenUsageGraph tokenUsage={t.props.token_usage} reasoningEffort={t.props.reasoning_effort} />
                        )}
                        {hasAgenticPlan && <AgentPlan query_plan={t.props?.query_plan ?? []} citation_details={citationDetails} />}
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
