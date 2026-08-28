import { useTranslation } from "react-i18next";

import styles from "./ClearChatButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

const ClearIcon = () => (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.buttonIcon}>
        <path d="M6 7h12" />
        <path d="M9 7V5.8A1.8 1.8 0 0 1 10.8 4h2.4A1.8 1.8 0 0 1 15 5.8V7" />
        <path d="M8 10v8.2A1.8 1.8 0 0 0 9.8 20h4.4A1.8 1.8 0 0 0 16 18.2V10" />
        <path d="M10.5 11.5v5" />
        <path d="M13.5 11.5v5" />
    </svg>
);

export const ClearChatButton = ({ className, disabled, onClick }: Props) => {
    const { t } = useTranslation();

    return (
        <button type="button" className={`${styles.button} ${className ?? ""}`} disabled={disabled} onClick={onClick}>
            <ClearIcon />
            <span>{t("clearChat")}</span>
        </button>
    );
};
