import React from "react";
import { TokenUsageGraph, TokenUsage } from "./TokenUsageGraph";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import styles from "./AnalysisPanel.module.css";
SyntaxHighlighter.registerLanguage("json", json);

type QueryPlanStep = {
    id: number;
    type: string;
    elapsed_ms?: number;
    knowledge_source_name?: string;
    search_index_arguments?: {
        search?: string;
        search_fields?: string[];
        semantic_configuration_name?: string;
        source_data_fields?: { name?: string }[];
    };
    web_arguments?: {
        search?: string;
    };
    query_time?: string;
    count?: number;
    input_tokens?: number;
    output_tokens?: number;
    reasoning_tokens?: number;
    retrieval_reasoning_effort?: {
        kind?: string;
    };
    [key: string]: unknown;
};

const STEP_LABELS: Record<string, string> = {
    modelQueryPlanning: "Query planning",
    searchIndex: "Search index",
    web: "Web search",
    agenticReasoning: "Agentic reasoning",
    modelAnswerSynthesis: "Answer synthesis"
};

const getStepLabel = (step: QueryPlanStep) => STEP_LABELS[step.type] ?? step.type;

const renderDetail = (step: QueryPlanStep) => {
    switch (step.type) {
        case "modelQueryPlanning": {
            const usage: TokenUsage = {
                prompt_tokens: step.input_tokens ?? 0,
                completion_tokens: step.output_tokens ?? 0,
                reasoning_tokens: 0,
                total_tokens: (step.input_tokens ?? 0) + (step.output_tokens ?? 0)
            };

            return <TokenUsageGraph tokenUsage={usage} labels={{ prompt: "Input Tokens", output: "Output Tokens", total: "Total" }} title="" />;
        }
        case "searchIndex": {
            const search = step.search_index_arguments?.search ?? "—";
            const sourceFields = (step.search_index_arguments?.source_data_fields ?? [])
                .map(field => field?.name)
                .filter((name): name is string => Boolean(name));
            return (
                <>
                    <div>
                        <strong>Source:</strong> {step.knowledge_source_name ?? "search index"}
                    </div>
                    <div className={styles.tQuery}>{search}</div>
                    {sourceFields.length > 0 && (
                        <div className={styles.tPropRow}>
                            {sourceFields.map(name => (
                                <span className={styles.tProp} key={name}>
                                    {name}
                                </span>
                            ))}
                        </div>
                    )}
                </>
            );
        }
        case "web": {
            const webSearch = step.web_arguments?.search ?? "—";
            return (
                <>
                    <div>
                        <strong>Source:</strong> {step.knowledge_source_name ?? "web"}
                    </div>
                    <div className={styles.tQuery}>{webSearch}</div>
                </>
            );
        }
        case "agenticReasoning": {
            const usage: TokenUsage = {
                prompt_tokens: 0,
                completion_tokens: step.reasoning_tokens ?? 0,
                reasoning_tokens: step.reasoning_tokens ?? 0,
                total_tokens: step.reasoning_tokens ?? 0
            };
            const effort = step.retrieval_reasoning_effort?.kind;

            return (
                <>
                    <TokenUsageGraph tokenUsage={usage} labels={{ total: "Agentic Reasoning Tokens" }} variant="totalOnly" title="" />
                    {effort && (
                        <div className={styles.tPropRow}>
                            <span className={styles.tProp}>Effort: {effort}</span>
                        </div>
                    )}
                </>
            );
        }
        case "modelAnswerSynthesis": {
            const usage: TokenUsage = {
                prompt_tokens: step.input_tokens ?? 0,
                completion_tokens: step.output_tokens ?? 0,
                reasoning_tokens: 0,
                total_tokens: (step.input_tokens ?? 0) + (step.output_tokens ?? 0)
            };

            return <TokenUsageGraph tokenUsage={usage} labels={{ prompt: "Input Tokens", output: "Output Tokens", total: "Total" }} title="" />;
        }
        default:
            return (
                <SyntaxHighlighter language="json" wrapLines wrapLongLines className={styles.tCodeBlock} style={a11yLight}>
                    {JSON.stringify(step, null, 2)}
                </SyntaxHighlighter>
            );
    }
};

interface Props {
    query_plan: QueryPlanStep[];
}

export const AgentPlan: React.FC<Props> = ({ query_plan }) => {
    return (
        <div>
            <div className={styles.header}>Execution steps</div>
            <table className={styles.subqueriesTable}>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Details</th>
                        <th>Elapsed MS</th>
                    </tr>
                </thead>
                <tbody>
                    {query_plan.map(step => (
                        <tr key={step.id}>
                            <td>{getStepLabel(step)}</td>
                            <td>{renderDetail(step)}</td>
                            <td title={step.query_time ?? undefined}>{step.elapsed_ms ?? "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
