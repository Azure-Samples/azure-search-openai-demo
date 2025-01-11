import { openDB, IDBPDatabase } from "idb";

export class FeedbackStore {
    private static instance: FeedbackStore;
    private readonly dbName = "ChatFeedbackDB";
    private readonly storeName = "feedback";
    private dbPromise: Promise<IDBDatabase>;
    private memoryCache: Map<string, number> = new Map();
    private initPromise: Promise<void>;
    private initialized = false;

    private constructor() {
        this.dbPromise = this.initializeDB();
        this.initPromise = this.loadAllFeedback();
    }

    public static getInstance(): FeedbackStore {
        if (!FeedbackStore.instance) {
            FeedbackStore.instance = new FeedbackStore();
        }
        return FeedbackStore.instance;
    }

    private initializeDB(): Promise<IDBDatabase> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);

            request.onerror = () => reject(request.error);

            request.onupgradeneeded = event => {
                const db = (event.target as IDBOpenDBRequest).result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName);
                }
            };

            request.onsuccess = () => resolve(request.result);
        });
    }

    private async loadAllFeedback(): Promise<void> {
        if (this.initialized) return;

        try {
            const db = await this.dbPromise;
            const tx = db.transaction(this.storeName, "readonly");
            const store = tx.objectStore(this.storeName);
            const keys = await new Promise<string[]>((resolve, reject) => {
                const request = store.getAllKeys();
                request.onsuccess = () => resolve(request.result as string[]);
                request.onerror = () => reject(request.error);
            });
            const values = await Promise.all(
                keys.map(async key => ({
                    key: key as string,
                    value: await new Promise<number | undefined>((resolve, reject) => {
                        const request = store.get(key);
                        request.onsuccess = () => resolve(request.result);
                        request.onerror = () => reject(request.error);
                    })
                }))
            );

            values.forEach(({ key, value }) => {
                if (value !== undefined) {
                    this.memoryCache.set(key, value);
                }
            });

            console.log("Loaded feedback cache:", Object.fromEntries(this.memoryCache));
            this.initialized = true;
        } catch (error) {
            console.error("Failed to load feedback cache:", error);
            throw error;
        }
    }

    async getFeedback(traceId: string): Promise<number | null> {
        await this.initPromise;

        // Check memory cache first
        if (this.memoryCache.has(traceId)) {
            return this.memoryCache.get(traceId) ?? null;
        }

        try {
            const db = await this.dbPromise;
            const transaction = db.transaction(this.storeName, "readonly");
            const store = transaction.objectStore(this.storeName);

            return new Promise((resolve, reject) => {
                const request = store.get(traceId);
                request.onsuccess = () => {
                    const value = request.result;
                    if (value !== undefined) {
                        this.memoryCache.set(traceId, value);
                    }
                    resolve(value ?? null);
                };
                request.onerror = () => reject(request.error);
            });
        } catch (error) {
            console.error(`FeedbackStore: Error getting feedback for ${traceId}:`, error);
            return null;
        }
    }

    async setFeedback(traceId: string, value: number): Promise<void> {
        await this.initPromise;

        try {
            const db = await this.dbPromise;
            const transaction = db.transaction(this.storeName, "readwrite");
            const store = transaction.objectStore(this.storeName);

            // Return a promise that only resolves when transaction is complete
            return new Promise((resolve, reject) => {
                transaction.oncomplete = () => {
                    this.memoryCache.set(traceId, value);
                    console.log(`FeedbackStore: Transaction completed for ${traceId}, value=${value}`);
                    resolve();
                };

                transaction.onerror = () => {
                    console.error(`FeedbackStore: Transaction failed for ${traceId}`, transaction.error);
                    reject(transaction.error);
                };

                const request = store.put(value, traceId);
                request.onerror = () => {
                    console.error(`FeedbackStore: Failed to store feedback=${value} for ${traceId}`, request.error);
                    reject(request.error);
                };
            });
        } catch (error) {
            console.error(`FeedbackStore: Error setting feedback for ${traceId}:`, error);
            throw error;
        }
    }

    async getAllFeedback(): Promise<Map<string, number>> {
        await this.initPromise;
        return new Map(this.memoryCache);
    }
}
