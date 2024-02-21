const BACKEND_URI = "";
import axios from "axios";

import {
    ChatAppResponse,
    ChatAppResponseOrError,
    ChatAppRequest,
    Config,
    EvaluationRequest,
    EvaluationResponse,
    Feedback,
    FeedbackResponse,
    ExperimentList,
    DocumentList
} from "./models";
import { useLogin, appServicesToken } from "../authConfig";

export function getHeaders(idToken: string | undefined): Record<string, string> {
    var headers: Record<string, string> = {
        "Content-Type": "application/json"
    };
    // If using login and not using app services, add the id token of the logged in account as the authorization
    if (useLogin && appServicesToken == null) {
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

export async function configApi(idToken: string | undefined): Promise<Config> {
    const response = await fetch(`${BACKEND_URI}/config`, {
        method: "GET",
        headers: getHeaders(idToken)
    });

    return (await response.json()) as Config;
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

export async function evalApi(request: EvaluationRequest, idToken: string | undefined): Promise<EvaluationResponse> {
    const response = await fetch(`${BACKEND_URI}/evaluate`, {
        method: "POST",
        headers: getHeaders(idToken),
        body: JSON.stringify(request)
    });
    const parsedResponse: EvaluationResponse = await response.json();

    return parsedResponse;
}

export async function postFeedbackApi(request: Feedback, idToken: string | undefined): Promise<Response> {
    return await fetch(`${BACKEND_URI}/feedback`, {
        method: "POST",
        headers: getHeaders(idToken),
        body: JSON.stringify(request)
    });
}

export async function getFeedbackApi(idToken: string | undefined): Promise<FeedbackResponse> {
    const response = await axios.get(`${BACKEND_URI}/feedback`, {
        headers: getHeaders(idToken)
    });

    return response.data as FeedbackResponse;
}

export async function getExperimentListApi(idToken: string | undefined): Promise<ExperimentList> {
    const response = await axios.get(`${BACKEND_URI}/experiment_list`, {
        headers: getHeaders(idToken)
    });

    return response.data as ExperimentList;
}

export async function getExperimentApi(id: string, idToken: string | undefined): Promise<any> {
    const response = await axios.get(`${BACKEND_URI}/experiment?name=${id}`, {
        headers: getHeaders(idToken)
    });

    return response.data;
}

export async function getDocsApi(idToken: string | undefined): Promise<DocumentList> {
    const response = await axios.get(`${BACKEND_URI}/documents`, {
        headers: getHeaders(idToken)
    });

    return response.data as DocumentList;
}

export async function getDocApi(id: string, idToken: string | undefined): Promise<any> {
    const response = await axios.get(`${BACKEND_URI}/content/${id}`, {
        headers: getHeaders(idToken)
    });

    return response.data;
}

export async function uploadFileApi(request: FormData, idToken: string | undefined): Promise<any> {
    try {
        // const formData = new FormData();
        // formData.append("file", file);

        // TODO :: we're sending it to wrong endpoint on purpose, bcs currently not working properly
        const response = await axios.post(`${BACKEND_URI}/upload`, request, {
            headers: {
                ...getHeaders(idToken),
                "Content-Type": "multipart/form-data"
            }
        });

        return response.data;
    } catch (e) {
        throw e;
    }
}
