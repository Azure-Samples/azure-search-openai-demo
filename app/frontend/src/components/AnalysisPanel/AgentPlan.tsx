import React from "react";
import { TokenUsageGraph, TokenUsage } from "./TokenUsageGraph";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import styles from "./AnalysisPanel.module.css";
import { QueryPlanStep, getStepLabel } from "./agentPlanUtils";
import { CitationDetail } from "../Answer/AnswerParser";
import { getCitationFilePath, WebDataPoint } from "../../api";
import answerStyles from "../Answer/Answer.module.css";
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
                    <div className={styles.tQuery}>{search}</div>
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
    query_plan: QueryPlanStep[];
    citation_details?: CitationDetail[];
    web_data_points?: WebDataPoint[];
    onEffortExtracted?: (effort: string | undefined) => void;
}

export const AgentPlan: React.FC<Props> = ({ query_plan, citation_details, web_data_points, onEffortExtracted }) => {
    const getCitationFontSize = React.useCallback((text: string) => {
        const length = text.length;
        if (length <= 45) {
            return "0.75em";
        }
        if (length <= 75) {
            return "0.7em";
        }
        if (length <= 110) {
            return "0.65em";
        }
        return "0.6em";
    }, []);

    const stepNumberLookup = React.useMemo(() => {
        const lookup: Record<string, number> = {};
        query_plan.forEach((step, index) => {
            if (step != null && step.id !== undefined && step.id !== null) {
                lookup[String(step.id)] = index + 1;
            }
        });
        return lookup;
    }, [query_plan]);

    const iterations = React.useMemo(() => {
        if (!query_plan || query_plan.length === 0) {
            return [] as QueryPlanStep[][];
        }

        const planningIndices = query_plan.reduce<number[]>((indices, step, index) => {
            if (step.type === "modelQueryPlanning") {
                indices.push(index);
            }
            return indices;
        }, []);

        if (planningIndices.length <= 1) {
            return [query_plan];
        }

        const iterationsList: QueryPlanStep[][] = [];
        const prePlanningSteps = planningIndices[0] > 0 ? query_plan.slice(0, planningIndices[0]) : [];

        planningIndices.forEach((planningIndex, idx) => {
            const nextPlanningIndex = planningIndices[idx + 1] ?? query_plan.length;
            const iterationSteps = query_plan.slice(planningIndex, nextPlanningIndex);

            if (idx === 0 && prePlanningSteps.length > 0) {
                iterationsList.push([...prePlanningSteps, ...iterationSteps]);
            } else if (iterationSteps.length > 0) {
                iterationsList.push(iterationSteps);
            }
        });

        return iterationsList;
    }, [query_plan]);

    React.useEffect(() => {
        // Extract effort from first agentic reasoning step
        const agenticStep = query_plan.find(step => step.type === "agenticReasoning");
        const effort = agenticStep?.retrieval_reasoning_effort?.kind;
        if (onEffortExtracted) {
            onEffortExtracted(effort);
        }
    }, [query_plan, onEffortExtracted]);

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
                                    const relatedCitations = citation_details
                                        ? citation_details.filter(detail => {
                                              return stepId !== undefined && detail.activityId === String(stepId);
                                          })
                                        : [];
                                    const sortedCitations = relatedCitations.length ? [...relatedCitations].sort((a, b) => a.index - b.index) : [];
                                    const stepNumber = stepId !== undefined ? stepNumberLookup[String(stepId)] : undefined;

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
                                                {sortedCitations.length > 0 && (
                                                    <div className={styles.stepCitations}>
                                                        {sortedCitations.map(detail => {
                                                            if (detail.isWeb) {
                                                                const matchingWebEntry = web_data_points?.find(entry => entry.url === detail.reference);
                                                                const webDisplayLabel = matchingWebEntry?.title?.trim()
                                                                    ? matchingWebEntry.title
                                                                    : detail.reference;
                                                                const citationText = `${detail.index}. ${webDisplayLabel}`;
                                                                return (
                                                                    <span
                                                                        key={`${step.id}-${detail.index}`}
                                                                        className={`${answerStyles.citationEntry} ${styles.stepCitationEntry}`}
                                                                    >
                                                                        <a
                                                                            className={answerStyles.citation}
                                                                            title={
                                                                                matchingWebEntry?.title?.trim()
                                                                                    ? `${matchingWebEntry.title} (${detail.reference})`
                                                                                    : detail.reference
                                                                            }
                                                                            href={detail.reference}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            style={{ fontSize: getCitationFontSize(citationText) }}
                                                                        >
                                                                            {citationText}
                                                                        </a>
                                                                    </span>
                                                                );
                                                            }

                                                            const path = getCitationFilePath(detail.reference);
                                                            const citationText = `${detail.index}. ${detail.reference}`;
                                                            return (
                                                                <span
                                                                    key={`${step.id}-${detail.index}`}
                                                                    className={`${answerStyles.citationEntry} ${styles.stepCitationEntry}`}
                                                                >
                                                                    <a
                                                                        className={answerStyles.citation}
                                                                        title={detail.reference}
                                                                        href={path}
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                        style={{ fontSize: getCitationFontSize(citationText) }}
                                                                    >
                                                                        {citationText}
                                                                    </a>
                                                                </span>
                                                            );
                                                        })}
                                                    </div>
                                                )}
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
