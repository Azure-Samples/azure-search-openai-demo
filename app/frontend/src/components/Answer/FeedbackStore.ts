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

    private async ensureInitialized(): Promise<void> {
        if (this.initialized) return;
        await this.initPromise;
    }

    async getFeedback(traceId: string): Promise<number | null> {
        await this.ensureInitialized();

        // First check memory cache
        const cached = this.memoryCache.get(traceId);
        if (cached !== undefined) {
            return cached;
        }

        try {
            const db = await this.dbPromise;
            const request = await db.transaction(this.storeName).objectStore(this.storeName).get(traceId);

            const value = request.result;

            if (value !== undefined) {
                this.memoryCache.set(traceId, value);
            }
            return value ?? null;
        } catch (error) {
            console.error(`Error getting feedback for ${traceId}:`, error);
            return null;
        }
    }

    async setFeedback(traceId: string, value: number): Promise<void> {
        await this.initPromise;

        try {
            const db = await this.dbPromise;
            const transaction = db.transaction(this.storeName, "readwrite");
            const store = transaction.objectStore(this.storeName);

            return new Promise((resolve, reject) => {
                const request = store.put(value, traceId);

                request.onsuccess = () => {
                    this.memoryCache.set(traceId, value);
                    console.log(`FeedbackStore: Stored feedback=${value} for ${traceId}`);
                    resolve();
                };

                request.onerror = () => {
                    console.error(`FeedbackStore: Failed to store feedback=${value} for ${traceId}`, request.error);
                    reject(request.error);
                };
            });
        } catch (error) {
            this.memoryCache.delete(traceId); // Remove from cache if storage fails
            throw error;
        }
    }

    async getAllFeedback(): Promise<Map<string, number>> {
        await this.initPromise;
        return new Map(this.memoryCache);
    }
}
