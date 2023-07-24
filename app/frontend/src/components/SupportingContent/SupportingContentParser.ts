import { getCitationFileName } from "../../api";

type ParsedSupportingContentItem = {
    title: string;
    link: string;
    content: string;
};

export function parseSupportingContentItem(item: string): ParsedSupportingContentItem {
    // Assumes the item starts with the file name followed by : and the content.
    // Example: "sdp_corporate.pdf: this is the content that follows".
    const parts = item.split(": ");
    const title = getCitationFileName(parts[0]);
    const link = parts[0];
    const content = parts.slice(1).join(": ");

    return {
        title,
        link,
        content
    };
}
