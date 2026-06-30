import { useTranslation } from "react-i18next";
import { Icon, IDropdownOption, Dropdown } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";

import { supportedLngs } from "./config";
import styles from "./LanguagePicker.module.css";

interface Props {
    onLanguageChange: (language: string) => void;
}

export const LanguagePicker = ({ onLanguageChange }: Props) => {
    const { i18n, t } = useTranslation();

    const handleLanguageChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<string>) => {
        onLanguageChange(option?.data || i18n.language);
    };

    const languagePickerId = useId("languagePicker");

    return (
        <div className={styles.languagePicker}>
            <Icon iconName="Globe" className={styles.languagePickerIcon as any} />
            <Dropdown
                id={languagePickerId}
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
