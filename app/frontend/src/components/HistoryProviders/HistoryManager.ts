import { useMemo } from "react";
import { IHistoryProvider, HistoryProviderOptions } from "../HistoryProviders/IProvider";
import { NoneProvider } from "../HistoryProviders/None";
import { IndexedDBProvider } from "../HistoryProviders/IndexedDB";
import { CosmosDBProvider } from "../HistoryProviders/CosmosDB";
import { MongoDBProvider } from "../HistoryProviders/MongoDB";

export const useHistoryManager = (provider: HistoryProviderOptions): IHistoryProvider => {
    const providerInstance = useMemo(() => {
        switch (provider) {
            case HistoryProviderOptions.IndexedDB:
                return new IndexedDBProvider("chat-database", "chat-history");
            case HistoryProviderOptions.CosmosDB:
                return new CosmosDBProvider();
            case HistoryProviderOptions.MongoDB:
                return new MongoDBProvider();
            case HistoryProviderOptions.None:
            default:
                return new NoneProvider();
        }
    }, [provider]);

    return providerInstance;
};
