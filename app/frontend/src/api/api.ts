const BACKEND_URI = "";

import { ChatAppResponse, ChatAppResponseOrError, ChatAppRequest, FileUploadRequest } from "./models";
import { useLogin } from "../authConfig";

function getHeaders(idToken: string | undefined, contentType: string | undefined = "application/json"): Record<string, string> {
    const headers: Record<string, string> = {};

    // Conditionally set the Content-Type header
    if (contentType) {
        headers["Content-Type"] = contentType;
    }

    // If using login, add the id token of the logged in account as the authorization
    if (useLogin && idToken) {
        headers["Authorization"] = `Bearer ${idToken}`;
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

export function getCitationFilePath(citation: string): string {
    return `${BACKEND_URI}/content/${citation}`;
}

export async function runScriptApi(request: ChatAppRequest, idToken: string | undefined): Promise<Response> {
    return await fetch(`${BACKEND_URI}/runScript`, {
        method: "POST",
        headers: getHeaders(idToken),
        body: JSON.stringify(request)
    });
}

export async function uploadFilesApi(request: FileUploadRequest, idToken: string | undefined): Promise<Response> {
    // Convert files to base64 and attach them to the request
    const base64Files: { name: string; content: string; type: string }[] = [];

    for (const file of request.files) {
        const base64 = await fileToBase64(file);
        base64Files.push({
            name: file.name,
            content: base64,
            type: file.type
        });
    }

    const payload = {
        ...request,
        files: base64Files
    };

    // Send the request as JSON
    return await fetch(`${BACKEND_URI}/uploadFiles`, {
        method: "POST",
        headers: getHeaders(idToken, "application/json"),
        body: JSON.stringify(payload)
    });
}

function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = error => reject(error);
        reader.readAsDataURL(file); // This method returns base64 encoded string
    });
}
