import i18next from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import HttpApi from "i18next-http-backend";
import { initReactI18next } from "react-i18next";

import enTranslation from "../locales/en/translation.json";
import esTranslation from "../locales/es/translation.json";
import jaTranslation from "../locales/ja/translation.json";
import frTranslation from "../locales/fr/translation.json";

export const supportedLngs: { [key: string]: { name: string; locale: string } } = {
    en: {
        name: "English",
        locale: "en-US"
    },
    es: {
        name: "Español",
        locale: "es-ES"
    },
    fr: {
        name: "Français",
        locale: "fr-FR"
    },
    ja: {
        name: "日本語",
        locale: "ja-JP"
    }
};

i18next
    .use(HttpApi)
    .use(LanguageDetector)
    .use(initReactI18next)
    // init i18next
    // for all options read: https://www.i18next.com/overview/configuration-options
    .init({
        resources: {
            en: { translation: enTranslation },
            es: { translation: esTranslation },
            fr: { translation: frTranslation },
            ja: { translation: jaTranslation }
        },
        fallbackLng: "en",
        supportedLngs: Object.keys(supportedLngs),
        debug: import.meta.env.DEV,
        interpolation: {
            escapeValue: false // not needed for react as it escapes by default
        }
    });

export default i18next;
