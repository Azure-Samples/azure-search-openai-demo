import { IDBPDatabase, openDB } from "idb";
import { IHistoryProvider, Answers, HistoryProviderOptions, HistoryMetaData } from "./IProvider";

export class IndexedDBProvider implements IHistoryProvider {
    getProviderName = () => HistoryProviderOptions.IndexedDB;

    private dbName: string;
    private storeName: string;
    private dbPromise: Promise<IDBPDatabase> | null = null;
    private cursorKey: IDBValidKey | undefined;
    private isCusorEnd: boolean = false;

    constructor(dbName: string, storeName: string) {
        this.dbName = dbName;
        this.storeName = storeName;
        this.cursorKey = undefined;
        this.isCusorEnd = false;
    }

    private async init() {
        const storeName = this.storeName;
        if (!this.dbPromise) {
            this.dbPromise = openDB(this.dbName, 1, {
                upgrade(db) {
                    if (!db.objectStoreNames.contains(storeName)) {
                        const store = db.createObjectStore(storeName, { keyPath: "id" });
                        store.createIndex("timestamp", "timestamp");
                    }
                }
            });
        }
        return this.dbPromise;
    }

    resetContinuationToken() {
        this.cursorKey = undefined;
        this.isCusorEnd = false;
    }

    async getNextItems(count: number): Promise<HistoryMetaData[]> {
        const db = await this.init();
        const tx = db.transaction(this.storeName, "readonly");
        const store = tx.objectStore(this.storeName);
        const index = store.index("timestamp");

        // return empty array if cursor is already at the end
        if (this.isCusorEnd) {
            return [];
        }

        // set cursor to the last key
        let cursor = this.cursorKey ? await index.openCursor(IDBKeyRange.upperBound(this.cursorKey), "prev") : await index.openCursor(null, "prev");

        // return empty array means no more history or no data. set isCursorEnd to true and return empty array
        if (!cursor) {
            this.isCusorEnd = true;
            return [];
        }

        const loadedItems: { id: string; title: string; timestamp: number; answers: Answers }[] = [];
        for (let i = 0; i < count && cursor; i++) {
            loadedItems.push(cursor.value);
            cursor = await cursor.continue();
        }

        // set isCursorEnd to true if cursor is null
        if (!cursor) {
            this.isCusorEnd = true;
        }

        // update cursorKey
        this.cursorKey = cursor?.key;

        return loadedItems;
    }

    async addItem(id: string, answers: Answers): Promise<void> {
        const timestamp = new Date().getTime();
        const db = await this.init(); // 自動的に初期化
        const tx = db.transaction(this.storeName, "readwrite");
        const current = await tx.objectStore(this.storeName).get(id);
        if (current) {
            await tx.objectStore(this.storeName).put({ ...current, id, timestamp, answers });
        } else {
            const title = answers[0][0].length > 50 ? answers[0][0].substring(0, 50) + "..." : answers[0][0];
            await tx.objectStore(this.storeName).add({ id, title, timestamp, answers });
        }
        await tx.done;
        return;
    }

    async getItem(id: string): Promise<Answers | null> {
        const db = await this.init();
        const tx = db.transaction(this.storeName, "readonly");
        const item = await tx.objectStore(this.storeName).get(id);
        return item ? item.answers : null;
    }

    async deleteItem(id: string): Promise<void> {
        const db = await this.init();
        await db.delete(this.storeName, id);
        return;
    }
}
