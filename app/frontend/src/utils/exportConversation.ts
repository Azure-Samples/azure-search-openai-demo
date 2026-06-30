import { ChatAppResponse } from "../api";

export type ConversationTurn = [user: string, response: ChatAppResponse];

// Serialize the in-memory conversation turns to a Markdown document with
// "## You" / "## Assistant" sections and a per-answer citation list.
export function conversationToMarkdown(answers: ConversationTurn[]): string {
    const lines: string[] = [];
    answers.forEach(([user, response]) => {
        lines.push("## You", "", user.trim(), "");
        lines.push("## Assistant", "", (response.output_text ?? "").trim(), "");

        const citations = response.context?.data_points?.citations ?? [];
        if (citations.length > 0) {
            lines.push("### Citations", "");
            citations.forEach((citation, index) => {
                lines.push(`${index + 1}. ${citation}`);
            });
            lines.push("");
        }
    });
    return lines.join("\n").trim() + "\n";
}

// Serialize the raw conversation turns (including thoughts and data points) to JSON.
export function conversationToJSON(answers: ConversationTurn[]): string {
    return JSON.stringify(answers, null, 2);
}

// Build a timestamped filename for an exported conversation, e.g. conversation_2024-01-31_14-05-09.md
export function exportConversationFilename(extension: string): string {
    const now = new Date();
    const pad = (value: number) => String(value).padStart(2, "0");
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(
        now.getMinutes()
    )}-${pad(now.getSeconds())}`;
    return `conversation_${timestamp}.${extension}`;
}

// Trigger a client-side download of the given content using a Blob and a temporary anchor.
export function downloadTextFile(content: string, filename: string, mimeType: string): void {
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
