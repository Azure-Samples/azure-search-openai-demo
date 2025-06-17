import { renderToStaticMarkup } from "react-dom/server";
import { ChatAppResponse, getCitationFilePath } from "../../api";

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: string[];
};

// Function to validate citation format and check if dataPoint starts with possible citation
function isCitationValid(contextDataPoints: any, citationCandidate: string): boolean {
    const trimmed = citationCandidate.trim();
    const regex = /.+\.[A-Za-z0-9]{1,}(?:#\S*)?$/;
    if (!regex.test(trimmed)) {
        return false;
    }

    // Determine the array of data points
    let dataPointsArray: string[];
    if (Array.isArray(contextDataPoints)) {
        dataPointsArray = contextDataPoints;
    } else if (contextDataPoints && Array.isArray(contextDataPoints.text)) {
        dataPointsArray = contextDataPoints.text;
    } else {
        return false;
    }

    return dataPointsArray.some(dp => dp.startsWith(trimmed));
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
            // Remove validation so every [filename] becomes a citation link
            // if (!isCitationValid(contextDataPoints, part)) {
            //     return `[${part}]`;
            // }
            const citationKey = part.trim();
            let citationIndex: number;

            if (citations.indexOf(citationKey) !== -1) {
                citationIndex = citations.indexOf(citationKey) + 1;
            } else {
                citations.push(citationKey);
                citationIndex = citations.length;
            }

            const path = getCitationFilePath(citationKey);

            return renderToStaticMarkup(
                <a className="supContainer" title={citationKey} onClick={() => onCitationClicked(path)}>
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
