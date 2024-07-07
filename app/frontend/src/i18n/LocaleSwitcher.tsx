import styles from "./LocaleSwitcher.module.css";
import { useTranslation } from "react-i18next";
import { LocalLanguage24Regular } from "@fluentui/react-icons";
import { supportedLngs } from "./config";

interface Props {
    onLanguageChange: (language: string) => void;
}

export const LocaleSwitcher = ({ onLanguageChange }: Props) => {
    const { i18n } = useTranslation();

    const handleLanguageChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        onLanguageChange(event.target.value);
    }

    return (
        <div className={styles.localeSwitcher}>
            <LocalLanguage24Regular className={styles.localeSwitcherIcon} />
            <select value={i18n.language} onChange={handleLanguageChange} className={styles.localeSwitcherText}>
                 {Object.entries(supportedLngs).map(([code, name]) => (
                    <option value={code} key={code}>
                        {name}
                    </option>
                ))}
            </select>            
        </div>
    );
}