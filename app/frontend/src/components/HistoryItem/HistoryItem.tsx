import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import styles from "./HistoryItem.module.css";
import { DefaultButton } from "@fluentui/react";
import { Delete24Regular } from "@fluentui/react-icons";

export interface HistoryData {
    id: string;
    title: string;
    timestamp: number;
}

interface HistoryItemProps {
    item: HistoryData;
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
}

export function HistoryItem({ item, onSelect, onDelete }: HistoryItemProps) {
    const [isModalOpen, setIsModalOpen] = useState(false);

    const handleDelete = useCallback(() => {
        setIsModalOpen(false);
        onDelete(item.id);
    }, [item.id, onDelete]);

    return (
        <div className={styles.historyItem}>
            <button onClick={() => onSelect(item.id)} className={styles.historyItemButton}>
                <div className={styles.historyItemTitle}>{item.title}</div>
            </button>
            <button onClick={() => setIsModalOpen(true)} className={styles.deleteButton} aria-label="delete this chat history">
                <Delete24Regular className={styles.deleteIcon} />
            </button>
            <DeleteHistoryModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onConfirm={handleDelete} />
        </div>
    );
}

function DeleteHistoryModal({ isOpen, onClose, onConfirm }: { isOpen: boolean; onClose: () => void; onConfirm: () => void }) {
    if (!isOpen) return null;
    const { t } = useTranslation();
    return (
        <div className={styles.modalOverlay}>
            <div className={styles.modalContent}>
                <h2 className={styles.modalTitle}>{t("history.deleteModalTitle")}</h2>
                <p className={styles.modalDescription}>{t("history.deleteModalDescription")}</p>
                <div className={styles.modalActions}>
                    <DefaultButton onClick={onClose} className={styles.modalCancelButton}>
                        {t("history.cancelLabel")}
                    </DefaultButton>
                    <DefaultButton onClick={onConfirm} className={styles.modalConfirmButton}>
                        {t("history.deleteLabel")}
                    </DefaultButton>
                </div>
            </div>
        </div>
    );
}
