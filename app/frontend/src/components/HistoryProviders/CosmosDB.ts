import { IHistoryProvider, Answers, HistoryProviderOptions, HistoryMetaData } from "./IProvider";
import { deleteChatHistoryApi, getChatHistoryApi, getChatHistoryListApi, postChatHistoryApi } from "../../api";

export class CosmosDBProvider implements IHistoryProvider {
    getProviderName = () => HistoryProviderOptions.CosmosDB;

    private continuationToken: string | undefined;
    private isItemEnd: boolean = false;

    resetContinuationToken() {
        this.continuationToken = undefined;
        this.isItemEnd = false;
    }

    async getNextItems(count: number, idToken?: string): Promise<HistoryMetaData[]> {
        if (this.isItemEnd) {
            return [];
        }

        try {
            const response = await getChatHistoryListApi(count, this.continuationToken, idToken || "");
            this.continuationToken = response.continuation_token;
            if (!this.continuationToken) {
                this.isItemEnd = true;
            }
            return response.items.map(item => ({
                id: item.id,
                title: item.title,
                timestamp: item.timestamp
            }));
        } catch (e) {
            console.error(e);
            return [];
        }
    }

    async addItem(id: string, answers: Answers, idToken?: string): Promise<void> {
        await postChatHistoryApi({ id, answers }, idToken || "");
        return;
    }

    async getItem(id: string, idToken?: string): Promise<Answers | null> {
        const response = await getChatHistoryApi(id, idToken || "");
        return response.answers || null;
    }

    async deleteItem(id: string, idToken?: string): Promise<void> {
        await deleteChatHistoryApi(id, idToken || "");
        return;
    }
}
