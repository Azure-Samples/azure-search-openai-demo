const BACKEND_URI = "";

import { AskRequest, ChatAppResponse, ChatAppResponseOrError, ChatRequest } from "./models";
import { useLogin } from "../authConfig";

function getHeaders(idToken: string | undefined): Record<string, string> {
    var headers : Record<string, string> = {
        "Content-Type": "application/json"
    };
    // If using login, add the id token of the logged in account as the authorization
    if (useLogin) {
        if (idToken) {
            headers["Authorization"] = `Bearer ${idToken}`
        }
    }

    return headers;
}

export async function askApi(options: AskRequest): Promise<ChatAppResponse> {
    const response = await fetch(`${BACKEND_URI}/ask`, {
        method: "POST",
        headers: getHeaders(options.idToken),
        body: JSON.stringify({
            question: options.question,
            overrides: {
                retrieval_mode: options.overrides?.retrievalMode,
                semantic_ranker: options.overrides?.semanticRanker,
                semantic_captions: options.overrides?.semanticCaptions,
                top: options.overrides?.top,
                temperature: options.overrides?.temperature,
                prompt_template: options.overrides?.promptTemplate,
                prompt_template_prefix: options.overrides?.promptTemplatePrefix,
                prompt_template_suffix: options.overrides?.promptTemplateSuffix,
                exclude_category: options.overrides?.excludeCategory,
                use_oid_security_filter: options.overrides?.useOidSecurityFilter,
                use_groups_security_filter: options.overrides?.useGroupsSecurityFilter
            }
        })
    });

    const parsedResponse: ChatAppResponseOrError = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error(parsedResponse.error || "Unknown error");
    }

    return parsedResponse as ChatAppResponse;
}

export async function chatApi(options: ChatRequest): Promise<Response> {
    const url = options.shouldStream ? "chat_stream" : "chat";
    return await fetch(`${BACKEND_URI}/${url}`, {
        method: "POST",
        headers: getHeaders(options.idToken),
        body: JSON.stringify({
            history: options.history,
            overrides: {
                retrieval_mode: options.overrides?.retrievalMode,
                semantic_ranker: options.overrides?.semanticRanker,
                semantic_captions: options.overrides?.semanticCaptions,
                top: options.overrides?.top,
                temperature: options.overrides?.temperature,
                prompt_template: options.overrides?.promptTemplate,
                prompt_template_prefix: options.overrides?.promptTemplatePrefix,
                prompt_template_suffix: options.overrides?.promptTemplateSuffix,
                exclude_category: options.overrides?.excludeCategory,
                suggest_followup_questions: options.overrides?.suggestFollowupQuestions,
                use_oid_security_filter: options.overrides?.useOidSecurityFilter,
                use_groups_security_filter: options.overrides?.useGroupsSecurityFilter
            }
        })
    });
}

export function getCitationFilePath(citation: string): string {
    return `${BACKEND_URI}/content/${citation}`;
}
