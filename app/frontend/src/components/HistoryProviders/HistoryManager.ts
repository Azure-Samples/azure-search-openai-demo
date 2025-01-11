import { useMemo } from "react";
import { IHistoryProvider, HistoryProviderOptions } from "./IProvider";
import { NoneProvider } from "./None";
import { IndexedDBProvider } from "./IndexedDB";
import { CosmosDBProvider } from "./CosmosDB";

export const useHistoryManager = (provider: HistoryProviderOptions): IHistoryProvider => {
    return useMemo(() => {
        switch (provider) {
            case HistoryProviderOptions.IndexedDB:
                return new IndexedDBProvider("chat-database", "chat-history");
            case HistoryProviderOptions.CosmosDB:
                return new CosmosDBProvider();
            case HistoryProviderOptions.None:
            default:
                return new NoneProvider();
        }
    }, [provider]);
};
