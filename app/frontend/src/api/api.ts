const BACKEND_URI = "";

import { ChatAppResponse, ChatAppResponseOrError, ChatAppRequest, UploadFilesRequest } from "./models";
import { useLogin } from "../authConfig";

function getHeaders(idToken: string | undefined): any {
    var headers: Record<string, string> = {
        "Content-Type": "application/json"
    };
    // If using login, add the id token of the logged in account as the authorization
    if (useLogin) {
        if (idToken) {
            headers["Authorization"] = `Bearer ${idToken}`;
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

export async function uploadFilesApi(request: UploadFilesRequest["files"], idToken: string | undefined, size:number): Promise<Response> {
    const headers = getHeaders(idToken);
    const contentLength = request.toString().length;
    const boundary = 'abcd'
    headers["Content-Length"] = size.toString();
    headers["Content-Type"] = 'multipart/form-data; boundary=' + boundary;
    return await fetch(`${BACKEND_URI}/upload`, {
        method: "POST",
        headers: headers,
        body: request
    });
}

export function getCitationFilePath(citation: string): string {
    return `${BACKEND_URI}/content/${citation}`;
}
