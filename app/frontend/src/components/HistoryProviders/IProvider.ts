import { ChatAppResponse } from "../../api";

export type HistoryMetaData = {
    id: string;
    title: string;
    timestamp: number;
    feedback?: number; // Add feedback field
};
export type Answers = [user: string, response: ChatAppResponse][];

export const enum HistoryProviderOptions {
    None = "none",
    IndexedDB = "indexedDB",
    CosmosDB = "cosmosDB"
}

export interface IHistoryProvider {
    getProviderName(): HistoryProviderOptions;
    resetContinuationToken(): void;
    getNextItems(count: number, idToken?: string): Promise<HistoryMetaData[]>;
    addItem(id: string, answers: Answers, idToken?: string): Promise<void>;
    getItem(id: string, idToken?: string): Promise<Answers | null>;
    deleteItem(id: string, idToken?: string): Promise<void>;
    updateFeedback(id: string, feedback: number): Promise<void>; // Add this method
}

export interface IFeedbackProvider {
    getFeedback(traceId: string): Promise<number | null>;
    setFeedback(traceId: string, value: number): Promise<void>;
    getAllFeedback(): Promise<Map<string, number>>;
}

export enum FeedbackProviderOptions {
    None = "none",
    IndexedDB = "indexeddb",
    CosmosDB = "cosmosdb"
}
