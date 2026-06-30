import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { supportedLngs } from "./config";
import styles from "./LanguagePicker.module.css";

interface Props {
    onLanguageChange: (language: string) => void;
}

const GlobeIcon = () => (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.languagePickerSvg}>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M3.8 9h16.4" />
        <path d="M3.8 15h16.4" />
        <path d="M12 3.5c2.2 2.2 3.3 5 3.3 8.5s-1.1 6.3-3.3 8.5" />
        <path d="M12 3.5c-2.2 2.2-3.3 5-3.3 8.5s1.1 6.3 3.3 8.5" />
    </svg>
);

const CheckIcon = () => (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.languagePickerCheck}>
        <path d="m5 12.5 4.3 4.1L19 7.5" />
    </svg>
);

const normalizeLanguage = (language: string) => {
    if (supportedLngs[language as keyof typeof supportedLngs]) {
        return language;
    }

    const baseLanguage = language.split("-")[0];
    return supportedLngs[baseLanguage as keyof typeof supportedLngs] ? baseLanguage : "en";
};

export const LanguagePicker = ({ onLanguageChange }: Props) => {
    const { i18n, t } = useTranslation();
    const [open, setOpen] = useState(false);
    const pickerRef = useRef<HTMLDivElement>(null);
    const selectedLanguage = normalizeLanguage(i18n.language);
    const languages = useMemo(() => Object.entries(supportedLngs), []);
    const selectedName = supportedLngs[selectedLanguage as keyof typeof supportedLngs]?.name ?? "English";

    useEffect(() => {
        if (!open) {
            return;
        }

        const handlePointerDown = (event: MouseEvent) => {
            if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
                setOpen(false);
            }
        };

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                setOpen(false);
            }
        };

        document.addEventListener("mousedown", handlePointerDown);
        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.removeEventListener("mousedown", handlePointerDown);
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [open]);

    const handleLanguageChange = (language: string) => {
        onLanguageChange(language);
        setOpen(false);
    };

    return (
        <div className={styles.languagePicker} ref={pickerRef}>
            <button
                type="button"
                className={styles.languagePickerButton}
                aria-label={t("labels.languagePicker")}
                aria-expanded={open}
                aria-haspopup="listbox"
                onClick={() => setOpen(current => !current)}
            >
                <GlobeIcon />
                <span className={styles.languagePickerLabel}>{selectedName}</span>
                <span className={styles.languagePickerCaret} aria-hidden="true" />
            </button>

            {open && (
                <div className={styles.languagePickerMenu} role="listbox" aria-label={t("labels.languagePicker")}>
                    {languages.map(([code, details]) => {
                        const selected = code === selectedLanguage;
                        return (
                            <button
                                key={code}
                                type="button"
                                role="option"
                                aria-selected={selected}
                                className={`${styles.languagePickerOption} ${selected ? styles.languagePickerOptionSelected : ""}`}
                                onClick={() => handleLanguageChange(code)}
                            >
                                <span>{details.name}</span>
                                {selected && <CheckIcon />}
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
