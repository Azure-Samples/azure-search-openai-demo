import { ChatAppResponse } from "../../api";

export type HistoryMetaData = { id: string; title: string; timestamp: number };
export type Answers = [user: string, response: ChatAppResponse][];

export const enum HistoryProviderOptions {
    None = "none",
    IndexedDB = "indexedDB"
}

export interface IHistoryProvider {
    getProviderName(): HistoryProviderOptions;
    resetContinuationToken(): void;
    getNextItems(count: number): Promise<HistoryMetaData[]>;
    addItem(id: string, answers: Answers): Promise<void>;
    getItem(id: string): Promise<Answers | null>;
    deleteItem(id: string): Promise<void>;
}
