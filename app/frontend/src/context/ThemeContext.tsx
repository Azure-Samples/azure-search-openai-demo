import React, { createContext, ReactNode, useContext, useEffect, useState, useCallback, useRef } from "react";

import defaultLogo from "../assets/defaultLogo.svg";
import customLogo from "../assets/customLogo.png";
import { CustomStyles, CustomText } from "../types";
import { GlobalStyleManager } from "../services/GlobalStyleManager";
// import chatLogo from "../assets/customLogoLetsgetnaked.png";

interface ThemeContextType {
    isDarkTheme: boolean;
    isBrandingEnabled: boolean;
    isShowingHeader: boolean;
    customText: CustomText;
    customStyles: CustomStyles;
    logo: string;
    toggleTheme: (isDark: boolean) => void;
    setCustomStyle: (styles: CustomStyles) => void;
    setCustomTexts: (texts: CustomText) => void;
    enableBranding: (enable: boolean) => void;
    toggleHeader: (show: boolean) => void;
}

const defaultCustomText: CustomText = {
    chatTitle: "Chat with Business Bot",
    chatSubtitle: "Ask anything or try an example",
    exampleQuestions: ["What information do you provide?", "What are the package prices?", "How do I get hold of someone?"]
};

const defaultCustomStylesLight: CustomStyles = {
    AccentHigh: "#692b61",
    AccentLight: "#f6d5f2",
    AccentDark: "#5e3c7d",
    TextColor: "#123f58",
    BackgroundColor: "#e3e3e3",
    ForegroundColor: "#4e5288",
    FormBackgroundColor: "#f5f5f5",
    BorderRadius: "10px",
    BorderWidth: "3px",
    FontBaseSize: "14px"
};

const defaultCustomStylesDark: CustomStyles = {
    AccentHigh: "#dcdef8",
    AccentLight: "#032219",
    AccentDark: "#fdfeff",
    TextColor: "#fdfeff",
    BackgroundColor: "#32343e",
    ForegroundColor: "#4e5288",
    FormBackgroundColor: "#32343e",
    BorderRadius: "10px",
    BorderWidth: "3px",
    FontBaseSize: "14px"
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
    const [isDarkTheme, setIsDarkTheme] = useState<boolean>(() => JSON.parse(localStorage.getItem("ms-azoaicc:isDarkTheme") ?? "false"));
    const [isBrandingEnabled, setEnableBranding] = useState<boolean>(() => JSON.parse(localStorage.getItem("ms-azoaicc:isBrandingEnabled") ?? "true"));
    const [isShowingHeader, setShowHeader] = useState<boolean>(() => JSON.parse(localStorage.getItem("ms-azoaicc:isShowingHeader") ?? "true"));
    const [customText, setCustomText] = useState<CustomText>(() =>
        JSON.parse(localStorage.getItem("ms-azoaicc:customText") ?? JSON.stringify(defaultCustomText))
    );
    const [customStyles, setCustomStyles] = useState<CustomStyles>(() =>
        JSON.parse(localStorage.getItem("ms-azoaicc:customStyles") ?? JSON.stringify(isDarkTheme ? defaultCustomStylesDark : defaultCustomStylesLight))
    );

    const logo = isBrandingEnabled ? customLogo : defaultLogo;

    const toggleTheme = useCallback((newIsDarkTheme: boolean) => {
        setIsDarkTheme(newIsDarkTheme);
        localStorage.setItem("ms-azoaicc:isDarkTheme", JSON.stringify(newIsDarkTheme));
        // Optionally, trigger style update logic here if theme-dependent styles need to be recalculated
    }, []);

    const setCustomStyle = useCallback((styles: CustomStyles) => {
        setCustomStyles(styles);
        localStorage.setItem("ms-azoaicc:customStyles", JSON.stringify(styles));
    }, []);

    const updateTheme = useCallback((styles: CustomStyles) => {
        GlobalStyleManager.applyCustomStyles(styles);
    }, []);

    const setCustomTexts = useCallback((newText: CustomText) => {
        setCustomText(newText);
        localStorage.setItem("ms-azoaicc:customText", JSON.stringify(newText));
    }, []);

    const enableBranding = useCallback((enabled: boolean) => {
        setEnableBranding(enabled);
        localStorage.setItem("ms-azoaicc:isBrandingEnabled", JSON.stringify(enabled));
    }, []);

    const toggleHeader = useCallback((show: boolean) => {
        setShowHeader(show);
        localStorage.setItem("ms-azoaicc:isShowingHeader", JSON.stringify(show));
    }, []);

    const contextValue = {
        isDarkTheme,
        isBrandingEnabled,
        isShowingHeader,
        customText,
        customStyles,
        logo,
        toggleTheme,
        setCustomStyle,
        setCustomTexts,
        enableBranding,
        toggleHeader,
        updateTheme
    };

    return <ThemeContext.Provider value={contextValue}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return context;
};
