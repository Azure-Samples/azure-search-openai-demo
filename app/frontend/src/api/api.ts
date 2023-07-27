import { AskRequest, AskResponse, BlobDocument, ChatRequest } from "./models";

export async function askApi(options: AskRequest): Promise<AskResponse> {
    const response = await fetch("/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            question: options.question,
            approach: options.approach,
            overrides: {
                semantic_ranker: options.overrides?.semanticRanker,
                semantic_captions: options.overrides?.semanticCaptions,
                top: options.overrides?.top,
                temperature: options.overrides?.temperature,
                prompt_template: options.overrides?.promptTemplate,
                prompt_template_prefix: options.overrides?.promptTemplatePrefix,
                prompt_template_suffix: options.overrides?.promptTemplateSuffix,
                exclude_category: options.overrides?.excludeCategory
            }
        })
    });

    const parsedResponse: AskResponse = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error(parsedResponse.error || "Unknown error");
    }

    return parsedResponse;
}

export async function chatApi(options: ChatRequest): Promise<AskResponse> {
    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            history: options.history,
            approach: options.approach,
            overrides: {
                semantic_ranker: options.overrides?.semanticRanker,
                semantic_captions: options.overrides?.semanticCaptions,
                top: options.overrides?.top,
                temperature: options.overrides?.temperature,
                prompt_template: options.overrides?.promptTemplate,
                prompt_template_prefix: options.overrides?.promptTemplatePrefix,
                prompt_template_suffix: options.overrides?.promptTemplateSuffix,
                exclude_category: options.overrides?.excludeCategory,
                suggest_followup_questions: options.overrides?.suggestFollowupQuestions
            }
        })
    });

    const parsedResponse: AskResponse = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error(parsedResponse.error || "Unknown error");
    }

    return parsedResponse;
}

export async function getDocumentNames() {
    const response = await fetch("/get_documents", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    });
    if (response.status > 299 || !response.ok) {
        const errorResponse = await response.json();
        throw Error(errorResponse.error || "Unknown error");
    }

    const parsedResponse: BlobDocument[] = await response.json();
    return parsedResponse;
}

export async function getSearch() {
    try {
        const response = await fetch("/get_search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Error:", error);
    }
}

export async function deleteDocument(blobName: string) {
    const response = await fetch("/delete_document", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: blobName
        })
    });

    if (response.status > 299 || !response.ok) {
        const errorResponse = await response.json();
        throw Error(errorResponse.error || "Unknown error");
    }

    return await response.text();
}

export async function deleteAllDocuments() {
    const response = await fetch("/delete_all_documents", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    });

    if (response.status > 299 || !response.ok) {
        const errorResponse = await response.json();
        throw Error(errorResponse.error || "Unknown error");
    }

    return await response.text();
}

export async function uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/upload_document", {
        method: "POST",
        body: formData
    });

    if (response.status > 299 || !response.ok) {
        const errorResponse = await response.json();
        throw Error(errorResponse.error || "Unknown error");
    }

    return await response.text();
}

export function getCitationFilePath(citation: string): string {
    return `/content/${citation}`;
}
