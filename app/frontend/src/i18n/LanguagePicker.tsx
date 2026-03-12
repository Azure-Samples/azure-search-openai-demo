import { useTranslation } from "react-i18next";
import { LocalLanguage24Regular } from "@fluentui/react-icons";
import { Dropdown, Option, OptionOnSelectData, SelectionEvents } from "@fluentui/react-components";
import { useId } from "react";

import { supportedLngs } from "./config";
import styles from "./LanguagePicker.module.css";

interface Props {
    onLanguageChange: (language: string) => void;
}

export const LanguagePicker = ({ onLanguageChange }: Props) => {
    const { i18n } = useTranslation();

    const handleLanguageChange = (_ev: SelectionEvents, data: OptionOnSelectData) => {
        onLanguageChange(data.optionValue || i18n.language);
    };
    const languagePickerId = useId();
    const { t } = useTranslation();

    return (
        <div className={styles.languagePicker}>
            <LocalLanguage24Regular className={styles.languagePickerIcon} />
            <Dropdown
                id={languagePickerId}
                selectedOptions={[i18n.language]}
                value={supportedLngs[i18n.language]?.name || i18n.language}
                onOptionSelect={handleLanguageChange}
                aria-label={t("labels.languagePicker")}
                appearance="underline"
            >
                {Object.entries(supportedLngs).map(([code, details]) => (
                    <Option key={code} value={code}>
                        {details.name}
                    </Option>
                ))}
            </Dropdown>
        </div>
    );
};
