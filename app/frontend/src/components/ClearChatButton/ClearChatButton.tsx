import { Delete24Regular } from "@fluentui/react-icons";
import { Button } from "@fluentui/react-components";
import { useTranslation } from "react-i18next";

import styles from "./ClearChatButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const ClearChatButton = ({ className, disabled, onClick }: Props) => {
    const { t, i18n } = useTranslation();
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <Button icon={<Delete24Regular />} disabled={disabled} onClick={onClick}>
                {t("clearChat")}
            </Button>
        </div>
    );
};
