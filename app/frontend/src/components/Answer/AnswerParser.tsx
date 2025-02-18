import { renderToStaticMarkup } from "react-dom/server";
import { ChatAppResponse, getCitationFilePath } from "../../api";
import { WebPage } from "../SupportingContent";

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: string[];
};

type Citation = {
    id: string;
    type: "document" | "web";
    citation: string | WebPage;
};

export function citationIdToCitation(citationId: string, contextDataPoints: any): Citation {
    // See if this is a web page citation
    const webSearch = contextDataPoints.web_search;
    if (Array.isArray(webSearch)) {
        const webPage = webSearch.find((page: WebPage) => page.id === citationId);
        if (webPage) {
            return {
                id: citationId,
                type: "web",
                citation: webPage
            };
        }
    }

    // Otherwise, assume it's a document citation
    return {
        id: citationId,
        type: "document",
        citation: citationId
    };
}

// Function to validate citation format and check if dataPoint starts with possible citation
function isCitationValid(contextDataPoints: any, citationCandidate: string): boolean {
    const regex = /.+\.\w{1,}(?:#\S*)?$/;
    if (!regex.test(citationCandidate)) {
        return false;
    }

    // Check if contextDataPoints is an object with a text property that is an array
    let dataPointsArray: string[];
    if (Array.isArray(contextDataPoints)) {
        dataPointsArray = contextDataPoints;
    } else if (contextDataPoints && Array.isArray(contextDataPoints.text)) {
        dataPointsArray = contextDataPoints.text;
    } else {
        return false;
    }
    // If there are web_sources, add those to the list of identifiers
    if (Array.isArray(contextDataPoints.web_search)) {
        contextDataPoints.web_search.forEach((source: any) => {
            if (source.id) {
                dataPointsArray.push(source.id);
            }
        });
    }

    const isValidCitation = dataPointsArray.some(dataPoint => {
        return dataPoint.startsWith(citationCandidate);
    });

    return isValidCitation;
}

export function parseAnswerToHtml(answer: ChatAppResponse, isStreaming: boolean, onCitationClicked: (citationFilePath: string) => void): HtmlParsedAnswer {
    const contextDataPoints = answer.context.data_points;
    const citations: string[] = [];

    // Trim any whitespace from the end of the answer after removing follow-up questions
    let parsedAnswer = answer.message.content.trim();

    // Omit a citation that is still being typed during streaming
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
        const truncatedAnswer = parsedAnswer.substring(0, lastIndex);
        parsedAnswer = truncatedAnswer;
    }

    const parts = parsedAnswer.split(/\[([^\]]+)\]/g);

    const fragments: string[] = parts.map((part, index) => {
        if (index % 2 === 0) {
            return part;
        } else {
            let citationIndex: number;

            if (!isCitationValid(contextDataPoints, part)) {
                return `[${part}]`;
            }

            if (citations.indexOf(part) !== -1) {
                citationIndex = citations.indexOf(part) + 1;
            } else {
                citations.push(part);
                citationIndex = citations.length;
            }

            const path = getCitationFilePath(part);

            return renderToStaticMarkup(
                <a className="supContainer" title={part} onClick={() => onCitationClicked(path)}>
                    <sup>{citationIndex}</sup>
                </a>
            );
        }
    });

    return {
        answerHtml: fragments.join(""),
        citations
    };
}
