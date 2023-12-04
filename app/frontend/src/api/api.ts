const BACKEND_URI = "";

import { ChatAppResponse, ChatAppResponseOrError, ChatAppRequest } from "./models";
import { useLogin } from "../authConfig";
import Cookies from "js-cookie";
import { v4 as uuidv4 } from 'uuid';

function getHeaders(idToken: string | undefined): Record<string, string> {
    var headers : Record<string, string> = {
        "Content-Type": "application/json",
        "Session-User-Id": getSessionUserId()
    };
    // If using login, add the id token of the logged in account as the authorization
    if (useLogin) {
        if (idToken) {
            headers["Authorization"] = `Bearer ${idToken}`
        }
    }

    return headers;
}

export async function askApi(request: ChatAppRequest, idToken: string | undefined): Promise<ChatAppResponse> {
    const response = await fetch(`${BACKEND_URI}/ask`, {
        method: "POST",
        headers: getHeaders(idToken),
        body: JSON.stringify(request)
    });

    const parsedResponse: ChatAppResponseOrError = await response.json();
    if (response.status > 299 || !response.ok) {
        throw Error(parsedResponse.error || "Unknown error");
    }

    return parsedResponse as ChatAppResponse;
}

export async function chatApi(request: ChatAppRequest, idToken: string | undefined): Promise<Response> {
    return await fetch(`${BACKEND_URI}/chat`, {
        method: "POST",
        headers: getHeaders(idToken),
        body: JSON.stringify(request)
    });
}

function getSessionUserId(): string {
    const sessionUserIdKey = 'sessionUserId';
    if (Cookies.get(sessionUserIdKey) !== undefined) {
        const farFutureDate = new Date(new Date().getFullYear() + 10, 0, 1);
        Cookies.set(sessionUserIdKey, uuidv4(), { expires: farFutureDate });
    }

    return Cookies.get(sessionUserIdKey)!!;
}

export function getCitationFilePath(citation: string): string {
    return `${BACKEND_URI}/content/${citation}`;
}
