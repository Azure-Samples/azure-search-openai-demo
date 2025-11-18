import React from "react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";

import { getCitationFilePath } from "../../api";
import { QueryPlanStep, getStepLabel } from "./agentPlanUtils";
import styles from "./AnalysisPanel.module.css";
import { TokenUsage, TokenUsageGraph } from "./TokenUsageGraph";

SyntaxHighlighter.registerLanguage("json", json);

const renderDetail = (step: QueryPlanStep) => {
    switch (step.type) {
        case "modelQueryPlanning": {
            const usage: TokenUsage = {
                prompt_tokens: step.input_tokens ?? 0,
                completion_tokens: step.output_tokens ?? 0,
                reasoning_tokens: 0,
                total_tokens: (step.input_tokens ?? 0) + (step.output_tokens ?? 0)
            };

            return <TokenUsageGraph tokenUsage={usage} labels={{ prompt: "Input", output: "Output", total: "Total tokens" }} title="" />;
        }
        case "searchIndex": {
            const search = step.search_index_arguments?.search ?? "—";
            return (
                <>
                    <div>
                        <strong>Source:</strong> {step.knowledge_source_name ?? "search index"}
                    </div>
                    <div>
                        <strong>Search:</strong> {search}
                    </div>
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
                    <div>
                        <strong>Search:</strong>
                        {webSearch}
                    </div>
                </>
            );
        }
        case "remoteSharePoint": {
            const sharepointSearch = step.remote_share_point_arguments?.search ?? "—";
            return (
                <>
                    <div>
                        <strong>Source:</strong> {step.knowledge_source_name ?? "SharePoint"}
                    </div>
                    <div>
                        <strong>Search: </strong>
                        {sharepointSearch}
                    </div>
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

            return (
                <>
                    <TokenUsageGraph tokenUsage={usage} labels={{ total: "Total tokens" }} variant="totalOnly" title="" />
                    <div style={{ fontSize: "0.85em", color: "#666", paddingLeft: "6px" }}>
                        This step uses Azure AI Search models, so the token capacity does not affect the deployed model.
                    </div>
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

            return <TokenUsageGraph tokenUsage={usage} labels={{ prompt: "Input", output: "Output", total: "Total tokens" }} title="" />;
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
    queryPlan: QueryPlanStep[];
    onEffortExtracted?: (effort: string | undefined) => void;
    onCitationClicked?: (citationFilePath: string) => void;
    results?: any[];
}

export const AgentPlan: React.FC<Props> = ({ queryPlan, onEffortExtracted, onCitationClicked, results }) => {
    // Helper to get search query for a step
    const getStepQuery = (step: QueryPlanStep): string | undefined => {
        if (step.search_index_arguments?.search) return step.search_index_arguments.search;
        if (step.web_arguments?.search) return step.web_arguments.search;
        if (step.remote_share_point_arguments?.search) return step.remote_share_point_arguments.search;
        return undefined;
    };

    // Helper to get results for a specific step
    const getResultsForStep = (step: QueryPlanStep): any[] => {
        if (!results || results.length === 0) return [];
        const stepQuery = getStepQuery(step);
        if (!stepQuery) return [];

        // Filter by both query and step type, then de-duplicate by filename
        const filtered = results.filter(result => result.activity?.query === stepQuery && result.type == step.type);
        const uniqueMap = new Map(filtered.map(r => [r.sourcepage || r.web_url || r.url, r]));
        return Array.from(uniqueMap.values());
    };

    const stepNumberLookup = React.useMemo(() => {
        const lookup: Record<string, number> = {};
        queryPlan.forEach((step, index) => {
            if (step != null && step.id !== undefined && step.id !== null) {
                lookup[String(step.id)] = index + 1;
            }
        });
        return lookup;
    }, [queryPlan]);

    const iterations = React.useMemo(() => {
        if (!queryPlan || queryPlan.length === 0) {
            return [] as QueryPlanStep[][];
        }

        const planningIndices = queryPlan.reduce<number[]>((indices, step, index) => {
            if (step.type === "modelQueryPlanning") {
                indices.push(index);
            }
            return indices;
        }, []);

        if (planningIndices.length <= 1) {
            return [queryPlan];
        }

        const iterationsList: QueryPlanStep[][] = [];
        const prePlanningSteps = planningIndices[0] > 0 ? queryPlan.slice(0, planningIndices[0]) : [];

        planningIndices.forEach((planningIndex, idx) => {
            const nextPlanningIndex = planningIndices[idx + 1] ?? queryPlan.length;
            const iterationSteps = queryPlan.slice(planningIndex, nextPlanningIndex);

            if (idx === 0 && prePlanningSteps.length > 0) {
                iterationsList.push([...prePlanningSteps, ...iterationSteps]);
            } else if (iterationSteps.length > 0) {
                iterationsList.push(iterationSteps);
            }
        });

        return iterationsList;
    }, [queryPlan]);

    React.useEffect(() => {
        // Extract effort from first agentic reasoning step
        const agenticStep = queryPlan.find(step => step.type === "agenticReasoning");
        const effort = agenticStep?.retrieval_reasoning_effort?.kind;
        if (onEffortExtracted) {
            onEffortExtracted(effort);
        }
    }, [queryPlan, onEffortExtracted]);

    if (iterations.length === 0) {
        return null;
    }

    return (
        <div>
            {iterations.map((iterationSteps, iterationIndex) => {
                const hasMultipleIterations = iterations.length > 1;
                const headerLabel = hasMultipleIterations ? `Iteration ${iterationIndex + 1} Execution steps` : "Execution steps";

                return (
                    <div className={styles.iterationSection} key={`iteration-${iterationIndex}`}>
                        <div className={styles.header}>{headerLabel}</div>
                        <table className={styles.subqueriesTable}>
                            <thead>
                                <tr>
                                    <th>Step</th>
                                    <th>Details</th>
                                    <th>Elapsed MS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {iterationSteps.map(step => {
                                    const stepId = step?.id;
                                    const stepNumber = stepId !== undefined ? stepNumberLookup[String(stepId)] : undefined;
                                    const stepResults = getResultsForStep(step);

                                    return (
                                        <tr key={step.id}>
                                            <td>
                                                <div className={styles.stepHeaderCell}>
                                                    {stepNumber && <span className={styles.stepNumberText}>{`Step ${stepNumber}:`}</span>}
                                                    <span className={styles.stepLabel}>{getStepLabel(step)}</span>
                                                </div>
                                            </td>
                                            <td>
                                                {renderDetail(step)}
                                                {(step.type === "searchIndex" || step.type === "remoteSharePoint" || step.type === "web") &&
                                                    (stepResults.length > 0 ? (
                                                        <div className={styles.stepResults}>
                                                            {stepResults.map((result, idx) => {
                                                                // Handle different result types
                                                                if (result.type === "remoteSharePoint" && result.web_url) {
                                                                    return (
                                                                        <div key={idx} className={styles.stepResult}>
                                                                            <a href={result.web_url} target="_blank" rel="noopener noreferrer">
                                                                                {result.title || result.web_url}
                                                                            </a>
                                                                        </div>
                                                                    );
                                                                } else if (result.url) {
                                                                    // Web result
                                                                    return (
                                                                        <div key={idx} className={styles.stepResult}>
                                                                            <a href={result.url} target="_blank" rel="noopener noreferrer">
                                                                                {result.title || result.url}
                                                                            </a>
                                                                        </div>
                                                                    );
                                                                } else if (result.sourcepage) {
                                                                    // Document result - make it clickable to open citation tab
                                                                    const path = getCitationFilePath(result.sourcepage);
                                                                    return (
                                                                        <div key={idx} className={styles.stepResult}>
                                                                            <a
                                                                                onClick={e => {
                                                                                    e.preventDefault();
                                                                                    if (onCitationClicked) {
                                                                                        onCitationClicked(path);
                                                                                    }
                                                                                }}
                                                                                style={{ cursor: "pointer" }}
                                                                            >
                                                                                {result.sourcepage}
                                                                            </a>
                                                                        </div>
                                                                    );
                                                                }
                                                                return null;
                                                            })}
                                                        </div>
                                                    ) : (
                                                        <div className={styles.noResults}>No results found</div>
                                                    ))}
                                            </td>
                                            <td title={step.query_time ?? undefined}>{step.elapsed_ms ?? "—"}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                );
            })}
        </div>
    );
};
