import { ChatAppResponse } from "../api";

export type ConversationTurns = [user: string, response: ChatAppResponse][];

function triggerDownload(content: string, mimeType: string, filename: string) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
}

function timestampedFilename(extension: string): string {
    const now = new Date();
    const pad = (value: number) => value.toString().padStart(2, "0");
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `conversation-${stamp}.${extension}`;
}

export function conversationToMarkdown(answers: ConversationTurns): string {
    const lines: string[] = [];

    answers.forEach(([question, response]) => {
        lines.push(`## You`);
        lines.push("");
        lines.push(question);
        lines.push("");
        lines.push(`## Assistant`);
        lines.push("");
        lines.push(response.output_text?.trim() || "");
        lines.push("");

        const citations = response.context?.data_points?.citations ?? [];
        if (citations.length > 0) {
            lines.push(`### Citations`);
            lines.push("");
            citations.forEach(citation => {
                lines.push(`- ${citation}`);
            });
            lines.push("");
        }
    });

    return lines.join("\n").trimEnd() + "\n";
}

export function conversationToJSON(answers: ConversationTurns): string {
    const turns = answers.map(([question, response]) => ({
        user: question,
        assistant: response
    }));
    return JSON.stringify(turns, null, 2);
}

export function exportConversationAsMarkdown(answers: ConversationTurns) {
    triggerDownload(conversationToMarkdown(answers), "text/markdown", timestampedFilename("md"));
}

export function exportConversationAsJSON(answers: ConversationTurns) {
    triggerDownload(conversationToJSON(answers), "application/json", timestampedFilename("json"));
}
