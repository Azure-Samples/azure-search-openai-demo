import { renderToStaticMarkup } from "react-dom/server";
import { ChatAppResponse, getCitationFilePath } from "../../api";

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: string[];
};

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

    // Process all anchor tags to ensure target="_blank"
    parsedAnswer = parsedAnswer.replace(/<a\s+([^>]*?)href=["']([^"']+)["']([^>]*?)>/gi, (match, before, href, after) => {
        // Check if target="_blank" already exists
        if (match.includes('target="_blank"') || match.includes("target='_blank'")) {
            return match;
        }
        // Add target="_blank" and rel="noopener noreferrer"
        // Make sure to include any existing attributes
        const existingRel = match.match(/rel=["']([^"']+)["']/);
        const relValue = existingRel ? existingRel[1] + " noopener noreferrer" : "noopener noreferrer";

        // Remove existing rel attribute if present
        let newMatch = match.replace(/rel=["'][^"']*["']/g, "");

        // Add target and rel attributes
        return newMatch.replace(/(<a\s+[^>]*?)(>)/gi, `$1 target="_blank" rel="${relValue}"$2`);
    });

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
