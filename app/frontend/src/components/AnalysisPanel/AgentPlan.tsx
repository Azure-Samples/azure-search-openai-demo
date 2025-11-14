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
        case "modelQueryPlanning":
            return (
                <div className={styles.tPropRow}>
                    <span className={styles.tProp}>Prompt tokens: {step.input_tokens ?? "—"}</span>
                    <span className={styles.tProp}>Completion tokens: {step.output_tokens ?? "—"}</span>
                </div>
            );
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
        case "agenticReasoning":
            return (
                <div className={styles.tPropRow}>
                    {step.retrieval_reasoning_effort?.kind && <span className={styles.tProp}>Effort: {step.retrieval_reasoning_effort.kind}</span>}
                    {typeof step.reasoning_tokens === "number" && <span className={styles.tProp}>Reasoning tokens: {step.reasoning_tokens}</span>}
                </div>
            );
        case "modelAnswerSynthesis":
            return (
                <div className={styles.tPropRow}>
                    <span className={styles.tProp}>Input tokens: {step.input_tokens ?? "—"}</span>
                    <span className={styles.tProp}>Output tokens: {step.output_tokens ?? "—"}</span>
                </div>
            );
        default:
            return (
                <SyntaxHighlighter language="json" wrapLines wrapLongLines className={styles.tCodeBlock} style={a11yLight}>
                    {JSON.stringify(step, null, 2)}
                </SyntaxHighlighter>
            );
    }
};

const renderMetric = (step: QueryPlanStep) => {
    switch (step.type) {
        case "searchIndex":
        case "web":
            return step.count ?? "—";
        case "modelQueryPlanning":
        case "modelAnswerSynthesis":
            if (step.input_tokens != null || step.output_tokens != null) {
                return `In: ${step.input_tokens ?? 0} / Out: ${step.output_tokens ?? 0}`;
            }
            return "—";
        case "agenticReasoning":
            return step.reasoning_tokens ?? "—";
        default:
            return "—";
    }
};

interface Props {
    query_plan: QueryPlanStep[];
    description: any;
}

export const AgentPlan: React.FC<Props> = ({ query_plan, description: _description }) => {
    const planning = query_plan.find(step => step.type === "modelQueryPlanning");
    const planningUsage: TokenUsage | undefined = planning
        ? {
              prompt_tokens: planning.input_tokens ?? 0,
              completion_tokens: planning.output_tokens ?? 0,
              reasoning_tokens: 0,
              total_tokens: (planning.input_tokens ?? 0) + (planning.output_tokens ?? 0)
          }
        : undefined;

    return (
        <div>
            {planningUsage && <TokenUsageGraph tokenUsage={planningUsage} />}

            <div className={styles.header}>Execution steps</div>
            <table className={styles.subqueriesTable}>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Details</th>
                        <th>Count / Tokens</th>
                        <th>Elapsed MS</th>
                    </tr>
                </thead>
                <tbody>
                    {query_plan.map(step => (
                        <tr key={step.id}>
                            <td>{getStepLabel(step)}</td>
                            <td>{renderDetail(step)}</td>
                            <td>{renderMetric(step)}</td>
                            <td title={step.query_time ?? undefined}>{step.elapsed_ms ?? "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
