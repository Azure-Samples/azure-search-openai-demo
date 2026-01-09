import { renderToStaticMarkup } from "react-dom/server";
import { ChatAppResponse, getCitationFilePath } from "../../api";
import { QueryPlanStep, getStepLabel, activityTypeLabels } from "../AnalysisPanel/agentPlanUtils";

export type CitationDetail = {
    reference: string;
    index: number;
    isWeb: boolean;
    activityId?: string;
    stepNumber?: number;
    stepLabel?: string;
    stepSource?: string;
};

type CitationFragment =
    | { type: "text"; value: string }
    | {
          type: "citation";
          detail: CitationDetail;
      };

type ActivityStepMeta = {
    stepNumber: number;
    stepLabel: string;
};

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: CitationDetail[];
};

const isWebCitation = (reference: string) => reference.startsWith("http://") || reference.startsWith("https://");

const normalizeAnswerText = (answer: ChatAppResponse, isStreaming: boolean): string => {
    let parsedAnswer = answer.message.content.trim();

    if (isStreaming) {
        let lastIndex = parsedAnswer.length;
        for (let i = parsedAnswer.length - 1; i >= 0; i--) {
            if (parsedAnswer[i] === "]") {
                break;
            } else if (parsedAnswer[i] === "[") {
                lastIndex = i;
                break;
            }
        }
        parsedAnswer = parsedAnswer.substring(0, lastIndex);
    }

    return parsedAnswer;
};

const buildActivityStepMap = (answer: ChatAppResponse): Record<string, ActivityStepMeta> => {
    const mapping: Record<string, ActivityStepMeta> = {};
    const thoughts = answer.context?.thoughts;
    if (!Array.isArray(thoughts)) {
        return mapping;
    }

    const thoughtWithPlan = thoughts.find(thought => Array.isArray(thought.props?.query_plan));
    if (!thoughtWithPlan) {
        return mapping;
    }

    const planSteps = (thoughtWithPlan.props?.query_plan as QueryPlanStep[]) ?? [];
    planSteps.forEach((step, index) => {
        if (step && step.id !== undefined && step.id !== null) {
            mapping[String(step.id)] = {
                stepNumber: index + 1,
                stepLabel: getStepLabel(step)
            };
        }
    });

    return mapping;
};

const collectCitations = (answer: ChatAppResponse, isStreaming: boolean): { fragments: CitationFragment[]; citations: CitationDetail[] } => {
    const possibleCitations = answer.context.data_points.citations || [];
    const citationActivityDetails = answer.context.data_points.citation_activity_details ?? {};
    const activitySteps = buildActivityStepMap(answer);
    const externalResults = answer.context.data_points.external_results_metadata || [];
    const parsedAnswer = normalizeAnswerText(answer, isStreaming);
    const parts = parsedAnswer.split(/\[([^\]]+)\]/g);

    // Helper to resolve SharePoint filename to URL
    const resolveSharePointUrl = (citation: string): string => {
        // If it's already a URL, return as-is
        if (isWebCitation(citation)) {
            return citation;
        }
        // Check if this looks like a filename (has an extension)
        const hasFileExtension = /\.(pdf|docx?|xlsx?|pptx?|txt|html?|csv)$/i.test(citation);
        if (!hasFileExtension) {
            return citation;
        }

        // Look for matching SharePoint URL in external_results_metadata
        // Match by checking if the URL ends with the filename
        const matchingResult = externalResults.find(result => {
            if (!result.url) return false;
            const urlParts = result.url.split("/");
            const urlFilename = urlParts[urlParts.length - 1];
            return urlFilename === citation || decodeURIComponent(urlFilename) === citation;
        });

        return matchingResult?.url || citation;
    };

    const fragments: CitationFragment[] = [];
    const citationMap = new Map<string, CitationDetail>();
    const citationList: CitationDetail[] = [];

    parts.forEach((part, index) => {
        if (index % 2 === 0) {
            fragments.push({ type: "text", value: part });
            return;
        }

        const isValidCitation = possibleCitations.some(citation => citation.endsWith(part));
        if (!isValidCitation) {
            fragments.push({ type: "text", value: `[${part}]` });
            return;
        }

        // Resolve SharePoint filename to URL if applicable
        const resolvedReference = resolveSharePointUrl(part);

        // Check if this resolved reference already exists
        const existing = citationMap.get(resolvedReference);
        if (existing) {
            fragments.push({ type: "citation", detail: existing });
            return;
        }

        const backendDetail = citationActivityDetails?.[part];
        const activityId = backendDetail?.id;
        const stepMeta = activityId ? activitySteps[String(activityId)] : undefined;

        // Get label from backend type using our mapping, or fallback to stepMeta
        const activityLabel = backendDetail?.type ? activityTypeLabels[backendDetail.type] || backendDetail.type : undefined;

        const detail: CitationDetail = {
            reference: resolvedReference,
            index: citationList.length + 1,
            isWeb: isWebCitation(resolvedReference),
            activityId: activityId !== undefined ? String(activityId) : undefined,
            stepNumber: backendDetail?.number ?? stepMeta?.stepNumber,
            stepLabel: activityLabel ?? stepMeta?.stepLabel,
            stepSource: backendDetail?.source
        };

        citationMap.set(resolvedReference, detail);
        citationList.push(detail);
        fragments.push({ type: "citation", detail });
    });

    return { fragments, citations: citationList };
};

const renderCitation = (detail: CitationDetail, onCitationClicked: (citationFilePath: string) => void) => {
    const stepBadgeLabel = detail.stepSource ?? detail.stepLabel;
    const stepBadgeTitle =
        detail.stepNumber !== undefined
            ? `Linked to Step ${detail.stepNumber}${detail.stepLabel ? `: ${detail.stepLabel}` : ""}${detail.stepSource ? ` (${detail.stepSource})` : ""}`
            : stepBadgeLabel
              ? `Linked to ${stepBadgeLabel}`
              : undefined;
    const supElement = <sup title={stepBadgeTitle ?? undefined}>{detail.index}</sup>;

    if (detail.isWeb) {
        return renderToStaticMarkup(
            <span className="citationBadgeContainer">
                <a
                    className="supContainer"
                    title={detail.reference}
                    href={detail.reference}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                >
                    {supElement}
                </a>
            </span>
        );
    }

    const path = getCitationFilePath(detail.reference);
    return renderToStaticMarkup(
        <span className="citationBadgeContainer">
            <a
                className="supContainer"
                title={detail.reference}
                onClick={e => {
                    e.preventDefault();
                    e.stopPropagation();
                    onCitationClicked(path);
                }}
            >
                {supElement}
            </a>
        </span>
    );
};

export function parseAnswerToHtml(answer: ChatAppResponse, isStreaming: boolean, onCitationClicked: (citationFilePath: string) => void): HtmlParsedAnswer {
    const { fragments, citations } = collectCitations(answer, isStreaming);
    const answerHtml = fragments.map(fragment => (fragment.type === "text" ? fragment.value : renderCitation(fragment.detail, onCitationClicked))).join("");

    return {
        answerHtml,
        citations
    };
}

export function extractCitationDetails(answer: ChatAppResponse, isStreaming = false): CitationDetail[] {
    return collectCitations(answer, isStreaming).citations;
}
