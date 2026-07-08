export type QueryPlanStep = {
    id: number | string;
    type: string;
    label?: string;
    elapsedMs?: number;
    knowledgeSourceName?: string;
    searchIndexArguments?: {
        search?: string;
        searchFields?: string[];
        semanticConfigurationName?: string;
        sourceDataFields?: { name?: string }[];
    };
    webArguments?: {
        search?: string;
    };
    remoteSharePointArguments?: {
        search?: string;
    };
    queryTime?: string;
    count?: number;
    inputTokens?: number;
    outputTokens?: number;
    reasoningTokens?: number;
    retrievalReasoningEffort?: {
        kind?: string;
    };
    [key: string]: unknown;
};

export const activityTypeLabels: Record<string, string> = {
    modelQueryPlanning: "Query planning",
    searchIndex: "Index search",
    web: "Web search",
    remoteSharePoint: "SharePoint search",
    agenticReasoning: "Agentic reasoning",
    modelAnswerSynthesis: "Answer synthesis"
};

export function getStepLabel(step: QueryPlanStep): string {
    return step.label || activityTypeLabels[step.type] || step.type;
}
