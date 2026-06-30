import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import styles from "./HistoryItem.module.css";

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

const DeleteIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.deleteIcon}>
    <path d="M6 7h12" />
    <path d="M9 7V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8V7" />
    <path d="M8 10v8.2A1.8 1.8 0 0 0 9.8 20h4.4A1.8 1.8 0 0 0 16 18.2V10" />
    <path d="M10.5 11.5v5" />
    <path d="M13.5 11.5v5" />
  </svg>
);

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

      <button
        onClick={() => setIsModalOpen(true)}
        className={styles.deleteButton}
        aria-label="Delete chat history"
        title="Delete"
      >
        <DeleteIcon />
      </button>

      <DeleteHistoryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={handleDelete}
      />
    </div>
  );
}

function DeleteHistoryModal({
  isOpen,
  onClose,
  onConfirm
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const { t } = useTranslation();
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <h2 className={styles.modalTitle}>{t("history.deleteModalTitle")}</h2>
        <p className={styles.modalDescription}>{t("history.deleteModalDescription")}</p>
        <div className={styles.modalActions}>
          <button type="button" onClick={onClose} className={styles.modalCancelButton}>
            {t("history.cancelLabel")}
          </button>
          <button type="button" onClick={onConfirm} className={styles.modalConfirmButton}>
            {t("history.deleteLabel")}
          </button>
        </div>
      </div>
    </div>
  );
}
