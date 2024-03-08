const BACKEND_URI = "";

import { ChatAppResponse, ChatAppResponseOrError, ChatAppRequest, Config, FileUploadResponse } from "./models";
import { useLogin, appServicesToken } from "../authConfig";

export function getHeaders(idToken: string | undefined): Record<string, string> {
    // If using login and not using app services, add the id token of the logged in account as the authorization
    if (useLogin && appServicesToken == null) {
        if (idToken) {
            return { Authorization: `Bearer ${idToken}` };
        }
    }

    return {};
}

export async function configApi(): Promise<Config> {
    const response = await fetch(`${BACKEND_URI}/config`, {
        method: "GET"
    });

    return (await response.json()) as Config;
}

export async function askApi(request: ChatAppRequest, idToken: string | undefined): Promise<ChatAppResponse> {
    const response = await fetch(`${BACKEND_URI}/ask`, {
        method: "POST",
        headers: { ...getHeaders(idToken), "Content-Type": "application/json" },
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
        headers: { ...getHeaders(idToken), "Content-Type": "application/json" },
        body: JSON.stringify(request)
    });
}

export function getCitationFilePath(citation: string): string {
    return `${BACKEND_URI}/content/${citation}`;
}

export async function uploadFileApi(request: FormData, idToken: string): Promise<FileUploadResponse> {
    // Send a POST request to the "/upload" endpoint with the provided form data
    const response = await fetch("/upload", {
        method: "POST",
        headers: getHeaders(idToken),
        body: request
    });

    // Check if the response status is not "OK".
    if (!response.ok) {
        throw new Error(`Uploading files failed: ${response.statusText}`);
    }

    // Parse the JSON response into the IUploadResponse type.
    const dataResponse: FileUploadResponse = await response.json();

    // Return the parsed data as the result of the Promise.
    return dataResponse;
}
