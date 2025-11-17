import { renderToStaticMarkup } from "react-dom/server";
import { ChatAppResponse, getCitationFilePath } from "../../api";
import { getStepLabel, QueryPlanStep } from "../AnalysisPanel/agentPlanUtils";

export type CitationDetail = {
    reference: string;
    index: number;
    isWeb: boolean;
    activityId?: string;
    stepNumber?: number;
    stepLabel?: string;
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
    const citationActivities: Record<string, string> = answer.context.data_points.citation_activities ?? {};
    const activitySteps = buildActivityStepMap(answer);
    const parsedAnswer = normalizeAnswerText(answer, isStreaming);
    const parts = parsedAnswer.split(/\[([^\]]+)\]/g);

    const fragments: CitationFragment[] = [];
    const citationMap = new Map<string, CitationDetail>();
    const citationList: CitationDetail[] = [];

    parts.forEach((part, index) => {
        if (index % 2 === 0) {
            fragments.push({ type: "text", value: part });
            return;
        }

        const isValidCitation = possibleCitations.some(citation => citation.startsWith(part));
        if (!isValidCitation) {
            fragments.push({ type: "text", value: `[${part}]` });
            return;
        }

        const existing = citationMap.get(part);
        if (existing) {
            fragments.push({ type: "citation", detail: existing });
            return;
        }

        const activityId = citationActivities?.[part];
        const stepMeta = activityId ? activitySteps[String(activityId)] : undefined;
        const detail: CitationDetail = {
            reference: part,
            index: citationList.length + 1,
            isWeb: isWebCitation(part),
            activityId: activityId !== undefined ? String(activityId) : undefined,
            stepNumber: stepMeta?.stepNumber,
            stepLabel: stepMeta?.stepLabel
        };

        citationMap.set(part, detail);
        citationList.push(detail);
        fragments.push({ type: "citation", detail });
    });

    return { fragments, citations: citationList };
};

const renderCitation = (detail: CitationDetail, onCitationClicked: (citationFilePath: string) => void) => {
    const supElement = <sup>{detail.index}</sup>;
    const stepBadge =
        detail.stepNumber !== undefined ? (
            <span
                className="citationStepBadge citationStepBadgeInline"
                title={`Linked to Step ${detail.stepNumber}${detail.stepLabel ? `: ${detail.stepLabel}` : ""}`}
            >
                {`Step ${detail.stepNumber}`}
            </span>
        ) : null;

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
                {stepBadge}
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
            {stepBadge}
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
