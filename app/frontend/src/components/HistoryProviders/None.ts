import { IHistoryProvider, Answers, HistoryProviderOptions, HistoryMetaData } from "./IProvider";

export class NoneProvider implements IHistoryProvider {
    getProviderName = () => HistoryProviderOptions.None;
    resetContinuationToken(): void {
        return;
    }
    async getNextItems(count: number): Promise<HistoryMetaData[]> {
        return [];
    }
    async addItem(id: string, answers: Answers): Promise<void> {
        return;
    }
    async getItem(id: string): Promise<null> {
        return null;
    }
    async deleteItem(id: string): Promise<void> {
        return;
    }
}
