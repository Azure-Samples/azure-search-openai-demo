import { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import { openDB, IDBPDatabase } from "idb";

type FeedbackState = {
    [traceId: string]: number;
};

interface FeedbackContextType {
    feedbackState: FeedbackState;
    setFeedback: (traceId: string, value: number) => Promise<void>;
    loadSavedFeedback: (traceId: string) => Promise<number | null>;
}

const FeedbackContext = createContext<FeedbackContextType>({
    feedbackState: {},
    setFeedback: async () => {},
    loadSavedFeedback: async () => null
});

export const FeedbackProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [feedbackState, setFeedbackState] = useState<FeedbackState>({});
    const dbRef = useRef<IDBPDatabase>();
    const initialized = useRef(false);

    // Consolidated cleanup function
    const cleanup = useCallback(() => {
        if (dbRef.current) {
            dbRef.current.close();
        }
        initialized.current = false;
        // Don't reset state on every cleanup - only when component unmounts
    }, []);

    // Single useEffect for initialization and cleanup
    useEffect(() => {
        const init = async () => {
            if (initialized.current) return;

            try {
                const db = await openDB("feedback-store", 1, {
                    upgrade(db) {
                        if (!db.objectStoreNames.contains("feedback")) {
                            db.createObjectStore("feedback");
                        }
                    }
                });
                dbRef.current = db;

                // Load existing feedback
                const tx = db.transaction("feedback", "readonly");
                const store = tx.objectStore("feedback");
                const keys = await store.getAllKeys();
                const values = await Promise.all(
                    keys.map(async key => ({
                        key: key as string,
                        value: await store.get(key)
                    }))
                );

                // Update state with existing feedback
                const newState: FeedbackState = {};
                values.forEach(({ key, value }) => {
                    if (value !== undefined) {
                        newState[key] = value;
                    }
                });

                setFeedbackState(newState);
                initialized.current = true;
                console.log("Feedback store initialized with:", newState);
            } catch (error) {
                console.error("Failed to initialize feedback store:", error);
            }
        };

        init();

        // Only reset state when component is unmounted
        return () => {
            cleanup();
            setFeedbackState({});
        };
    }, [cleanup]);

    const setFeedback = useCallback(async (traceId: string, value: number) => {
        if (!dbRef.current) {
            throw new Error("Feedback store not initialized");
        }

        try {
            // Update DB first
            await dbRef.current.put("feedback", value, traceId);

            // Only update state if DB operation succeeded
            setFeedbackState(prev => {
                const newState = { ...prev, [traceId]: value };
                console.log(`Updated feedback state for ${traceId}:`, newState);
                return newState;
            });
        } catch (error) {
            console.error(`Failed to set feedback for ${traceId}:`, error);
            throw error;
        }
    }, []);

    const loadSavedFeedback = useCallback(
        async (traceId: string): Promise<number | null> => {
            // Check memory state first
            if (feedbackState[traceId] !== undefined) {
                return feedbackState[traceId];
            }

            if (!dbRef.current) {
                console.warn("Feedback store not initialized");
                return null;
            }

            try {
                const value = await dbRef.current.get("feedback", traceId);
                if (value !== undefined) {
                    setFeedbackState(prev => ({ ...prev, [traceId]: value }));
                }
                return value ?? null;
            } catch (error) {
                console.error(`Failed to load feedback for ${traceId}:`, error);
                return null;
            }
        },
        [feedbackState]
    );

    return <FeedbackContext.Provider value={{ feedbackState, setFeedback, loadSavedFeedback }}>{children}</FeedbackContext.Provider>;
};

export const useFeedback = () => useContext(FeedbackContext);
