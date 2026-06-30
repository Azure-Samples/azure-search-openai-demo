import { useTranslation } from "react-i18next";

import styles from "./HistoryButton.module.css";

interface Props {
  className?: string;
  onClick: () => void;
  disabled?: boolean;
}

const HistoryIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.buttonIcon}>
    <path d="M4 12a8 8 0 1 0 2.35-5.65" />
    <path d="M4 5v5h5" />
    <path d="M12 8v4l2.5 2" />
  </svg>
);

export const HistoryButton = ({ className, disabled, onClick }: Props) => {
  const { t } = useTranslation();

  return (
    <button
      type="button"
      className={`${styles.button} ${className ?? ""}`}
      disabled={disabled}
      onClick={onClick}
    >
      <HistoryIcon />
      <span>{t("history.openChatHistory")}</span>
    </button>
  );
};
