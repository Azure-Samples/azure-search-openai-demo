import { ArrowDownload24Regular } from "@fluentui/react-icons";
import { Menu, MenuTrigger, MenuButton, MenuPopover, MenuList, MenuItem } from "@fluentui/react-components";
import { useTranslation } from "react-i18next";

import styles from "./ExportButton.module.css";

interface Props {
    className?: string;
    disabled?: boolean;
    onExportMarkdown: () => void;
    onExportJSON: () => void;
}

export const ExportButton = ({ className, disabled, onExportMarkdown, onExportJSON }: Props) => {
    const { t } = useTranslation();
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <Menu>
                <MenuTrigger disableButtonEnhancement>
                    <MenuButton icon={<ArrowDownload24Regular />} disabled={disabled}>
                        {t("exportConversation.buttonLabel")}
                    </MenuButton>
                </MenuTrigger>
                <MenuPopover>
                    <MenuList>
                        <MenuItem onClick={onExportMarkdown}>{t("exportConversation.markdown")}</MenuItem>
                        <MenuItem onClick={onExportJSON}>{t("exportConversation.json")}</MenuItem>
                    </MenuList>
                </MenuPopover>
            </Menu>
        </div>
    );
};
