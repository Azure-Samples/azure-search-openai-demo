import { Panel, PanelType } from "@fluentui/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { HistoryData, HistoryItem } from "../HistoryItem";
import { Answers, HistoryProviderOptions } from "../HistoryProviders/IProvider";
import { useHistoryManager, HistoryMetaData } from "../HistoryProviders";
import { useTranslation } from "react-i18next";
import styles from "./HistoryPanel.module.css";

const HISTORY_COUNT_PER_LOAD = 20;

export const HistoryPanel = ({
    provider,
    isOpen,
    notify,
    onClose,
    onChatSelected
}: {
    provider: HistoryProviderOptions;
    isOpen: boolean;
    notify: boolean;
    onClose: () => void;
    onChatSelected: (answers: Answers) => void;
}) => {
    const historyManager = useHistoryManager(provider);
    const [history, setHistory] = useState<HistoryMetaData[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [hasMoreHistory, setHasMoreHistory] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        if (notify) {
            setHistory([]);
            historyManager.resetContinuationToken();
            setHasMoreHistory(true);
        }
    }, [isOpen, notify]);

    const loadMoreHistory = async () => {
        setIsLoading(() => true);
        const items = await historyManager.getNextItems(HISTORY_COUNT_PER_LOAD);
        if (items.length === 0) {
            setHasMoreHistory(false);
        }
        setHistory(prevHistory => [...prevHistory, ...items]);
        setIsLoading(() => false);
    };

    const handleSelect = async (id: string) => {
        const item = await historyManager.getItem(id);
        if (item) {
            onChatSelected(item);
        }
    };

    const handleDelete = async (id: string) => {
        await historyManager.deleteItem(id);
        setHistory(prevHistory => prevHistory.filter(item => item.id !== id));
    };

    const groupedHistory = useMemo(() => groupHistory(history), [history]);

    const { t } = useTranslation();

    return (
        <Panel
            type={PanelType.customNear}
            style={{ padding: "0px" }}
            headerText={t("history.chatHistory")}
            customWidth="300px"
            isBlocking={false}
            isOpen={isOpen}
            onDismiss={() => onClose()}
            onDismissed={() => {
                setHistory([]);
                setHasMoreHistory(true);
                historyManager.resetContinuationToken();
            }}
        >
            <div>
                {Object.entries(groupedHistory).map(([group, items]) => (
                    <div key={group} className={styles.group}>
                        <p className={styles.groupLabel}>{t(group)}</p>
                        {items.map(item => (
                            <HistoryItem key={item.id} item={item} onSelect={handleSelect} onDelete={handleDelete} />
                        ))}
                    </div>
                ))}
                {history.length === 0 && <p>{t("history.noHistory")}</p>}
                {hasMoreHistory && !isLoading && <InfiniteLoadingButton func={loadMoreHistory} />}
            </div>
        </Panel>
    );
};

function groupHistory(history: HistoryData[]) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    const lastMonth = new Date(today);
    lastMonth.setDate(lastMonth.getDate() - 30);

    return history.reduce(
        (groups, item) => {
            const itemDate = new Date(item.timestamp);
            let group;

            if (itemDate >= today) {
                group = "history.today";
            } else if (itemDate >= yesterday) {
                group = "history.yesterday";
            } else if (itemDate >= lastWeek) {
                group = "history.last7days";
            } else if (itemDate >= lastMonth) {
                group = "history.last30days";
            } else {
                group = itemDate.toLocaleDateString(undefined, { year: "numeric", month: "long" });
            }

            if (!groups[group]) {
                groups[group] = [];
            }
            groups[group].push(item);
            return groups;
        },
        {} as Record<string, HistoryData[]>
    );
}

const InfiniteLoadingButton = ({ func }: { func: () => void }) => {
    const buttonRef = useRef(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        if (buttonRef.current) {
                            func();
                        }
                    }
                });
            },
            {
                root: null,
                threshold: 0
            }
        );

        if (buttonRef.current) {
            observer.observe(buttonRef.current);
        }

        return () => {
            if (buttonRef.current) {
                observer.unobserve(buttonRef.current);
            }
        };
    }, []);

    return <button ref={buttonRef} onClick={func} />;
};
