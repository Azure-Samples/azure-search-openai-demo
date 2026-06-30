import { ArrowDownload24Regular } from "@fluentui/react-icons";
import { Button, Menu, MenuTrigger, MenuPopover, MenuList, MenuItem } from "@fluentui/react-components";
import { useTranslation } from "react-i18next";

import styles from "./ExportButton.module.css";

interface Props {
    className?: string;
    onExportMarkdown: () => void;
    onExportJSON: () => void;
    disabled?: boolean;
}

export const ExportButton = ({ className, disabled, onExportMarkdown, onExportJSON }: Props) => {
    const { t } = useTranslation();
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <Menu>
                <MenuTrigger disableButtonEnhancement>
                    <Button icon={<ArrowDownload24Regular />} disabled={disabled}>
                        {t("exportChat")}
                    </Button>
                </MenuTrigger>
                <MenuPopover>
                    <MenuList>
                        <MenuItem onClick={onExportMarkdown}>{t("export.markdown")}</MenuItem>
                        <MenuItem onClick={onExportJSON}>{t("export.json")}</MenuItem>
                    </MenuList>
                </MenuPopover>
            </Menu>
        </div>
    );
};
