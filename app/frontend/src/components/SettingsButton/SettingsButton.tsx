import { Button } from "@fluentui/react-components";
import { Icon } from "@fluentui/react";
import { useTranslation } from "react-i18next";

import styles from "./SettingsButton.module.css";

interface Props {
  className?: string;
  onClick: () => void;
}

export const SettingsButton = ({ className, onClick }: Props) => {
  const { t } = useTranslation();
  return (
    <div className={`${styles.container} ${className ?? ""}`}>
      {/* Хэрэв буцааж гаргах бол:
      <Button icon={<Icon iconName="Settings" />} onClick={onClick}>
        {t("developerSettings")}
      </Button>
      */}
    </div>
  );
};
