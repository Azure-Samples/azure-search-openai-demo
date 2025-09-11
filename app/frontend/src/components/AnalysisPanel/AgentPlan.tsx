import React from "react";
import { TokenUsageGraph, TokenUsage } from "./TokenUsageGraph";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import styles from "./AnalysisPanel.module.css";
SyntaxHighlighter.registerLanguage("json", json);

type ModelQueryPlanningStep = {
    id: number;
    type: "modelQueryPlanning";
    input_tokens: number;
    output_tokens: number;
};

type AzureSearchQueryStep = {
    id: number;
    type: "searchIndex";
    knowledge_source_name: string;
    search_index_arguments: { search: string };
    query_time: string;
    count: number;
    elapsed_ms: number;
};

type Step = ModelQueryPlanningStep | AzureSearchQueryStep;

interface Props {
    query_plan: Step[];
    description: any;
}

export const AgentPlan: React.FC<Props> = ({ query_plan, description }) => {
    // find the planning step
    const planning = query_plan.find((step): step is ModelQueryPlanningStep => step.type === "modelQueryPlanning");

    // collect all search query steps
    const queries = query_plan.filter((step): step is AzureSearchQueryStep => step.type === "searchIndex");

    return (
        <div>
            {planning && (
                <TokenUsageGraph
                    tokenUsage={
                        {
                            prompt_tokens: planning.input_tokens,
                            completion_tokens: planning.output_tokens,
                            reasoning_tokens: 0,
                            total_tokens: planning.input_tokens + planning.output_tokens
                        } as TokenUsage
                    }
                />
            )}

            <div className={styles.header}>Subqueries</div>
            {queries.length > 0 && (
                <table className={styles.subqueriesTable}>
                    <thead>
                        <tr>
                            <th>Subquery</th>
                            <th>Total Result Count</th>
                            <th>Elapsed MS</th>
                        </tr>
                    </thead>
                    <tbody>
                        {queries.map(q => (
                            <tr key={q.id}>
                                <td>{q.search_index_arguments.search}</td>
                                <td>{q.count}</td>
                                <td>{q.elapsed_ms}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};
