import { useTranslation } from "react-i18next";
import { LocalLanguage24Regular } from "@fluentui/react-icons";
import { IDropdownOption, Dropdown } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";

import { supportedLngs } from "./config";
import styles from "./LocaleSwitcher.module.css";

interface Props {
    onLanguageChange: (language: string) => void;
}

export const LocaleSwitcher = ({ onLanguageChange }: Props) => {
    const { i18n } = useTranslation();

    const handleLanguageChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<String> | undefined) => {
        onLanguageChange(option?.data || i18n.language);
    };
    const localeSwitcherId = useId("localSwitcher");
    const { t } = useTranslation();

    return (
        <div className={styles.localeSwitcher}>
            <LocalLanguage24Regular className={styles.localeSwitcherIcon} />
            <Dropdown
                id={localeSwitcherId}
                selectedKey={i18n.language}
                options={Object.entries(supportedLngs).map(([code, details]) => ({
                    key: code,
                    text: details.name,
                    selected: code === i18n.language,
                    data: code
                }))}
                onChange={handleLanguageChange}
                ariaLabel={t("labels.languagePicker")}
            />
        </div>
    );
};
