import { Button } from "@fluentui/react-components";
import { Icon } from "@fluentui/react";
import { useTranslation } from "react-i18next";

import styles from "./ClearChatButton.module.css";

interface Props {
  className?: string;
  onClick: () => void;
  disabled?: boolean;
}

export const ClearChatButton = ({ className, disabled, onClick }: Props) => {
  const { t } = useTranslation();

  return (
    <div className={`${styles.container} ${className ?? ""}`}>
      <Button
        icon={<Icon iconName="Delete" />}
        disabled={disabled}
        onClick={onClick}
      >
        {t("clearChat")}
      </Button>
    </div>
  );
};
