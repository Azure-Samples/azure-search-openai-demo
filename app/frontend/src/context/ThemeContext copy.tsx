// src/context/ThemeContext.tsx
import { createContext, useContext, ReactNode, useState, useEffect, useRef, useCallback } from "react";

import defaultLogo from "../assets/defaultLogo.svg";
import customLogo from "../assets/customLogo.png";
import chatLogo from "../assets/customLogoLetsgetnaked.png";

import { CustomStylesState } from "../components/SettingsStyles";

type CustomTextType = {
    chatTitle: string;
    chatSubtitle: string;
    exampleQuestions: string[];
};

// type Theme = "light" | "dark";
interface ThemeContextType {
    // theme: Theme;
    logo: string;
    chatLogo: string;
    isDarkTheme: boolean;
    isBrandingEnabled: boolean;
    isShowingHeader: boolean;
    toggleTheme: (newIsDarkTheme: boolean) => void;
    toggleHeader: (show: boolean) => void;
    setCustomStyle: (newStyles: CustomStylesState) => void;
    setCustomTexts: (newTexts: CustomTextType) => void;
    enableBranding: (enable: boolean) => void;
    customText: CustomTextType;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
    // const [theme, setTheme] = useState<Theme>("light");

    const [isBrandingEnabled, setEnableBranding] = useState(() => {
        const storedBranding = localStorage.getItem("ms-azoaicc:isBrandingEnabled");
        return storedBranding ? JSON.parse(storedBranding) : true;
    });

    const [isDarkTheme, setIsDarkTheme] = useState(() => {
        const storedTheme = localStorage.getItem("ms-azoaicc:isDarkTheme");
        return storedTheme ? JSON.parse(storedTheme) : false;
    });

    const [isShowingHeader, setShowHeader] = useState(() => {
        const storedHeader = localStorage.getItem("ms-azoaicc:isShowingHeader");
        return storedHeader ? JSON.parse(storedHeader) : true;
    });

    const [customText, setCustomText] = useState(() => {
        const storedText = localStorage.getItem("ms-azoaicc:customText");
        return storedText
            ? JSON.parse(storedText)
            : {
                  chatTitle: "Chat with Business Bot",
                  chatSubtitle: "Ask anything or try an example",
                  exampleQuestions: ["What information do you provide?", "What are the package prices?", "How do I get hold of someone?"]
              };
    });

    const [customStyles, setCustomStyles] = useState(() => {
        const styleDefaultsLight = {
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

        const styleDefaultsDark = {
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
        const defaultStyles = isDarkTheme ? styleDefaultsDark : styleDefaultsLight;
        const storedStyles = localStorage.getItem("ms-azoaicc:customStyles");
        return storedStyles ? JSON.parse(storedStyles) : defaultStyles;
    });

    const [isLoading] = useState<boolean>(false);

    const logo = isBrandingEnabled ? customLogo : defaultLogo;

    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        // Update the state when local storage changes
        const handleStorageChange = () => {
            const storedStyles = localStorage.getItem("ms-azoaicc:customStyles");
            if (storedStyles) {
                setCustomStyles(JSON.parse(storedStyles));
            }

            const storedBranding = localStorage.getItem("ms-azoaicc:isBrandingEnabled");
            if (storedBranding) {
                setEnableBranding(JSON.parse(storedBranding));
            }

            const storedTheme = localStorage.getItem("ms-azoaicc:isDarkTheme");
            if (storedTheme) {
                setIsDarkTheme(JSON.parse(storedTheme));
            }

            const storedText = localStorage.getItem("ms-azoaicc:customText");
            if (storedText) {
                setCustomText(JSON.parse(storedText));
            }
        };

        // Attach the event listener
        window.addEventListener("storage", handleStorageChange);

        // Store customStyles in local storage whenever it changes
        localStorage.setItem("ms-azoaicc:customStyles", JSON.stringify(customStyles));

        // Store isBrandingEnabled in local storage whenever it changes
        localStorage.setItem("ms-azoaicc:isBrandingEnabled", JSON.stringify(isBrandingEnabled));

        // Store isDarkTheme in local storage whenever it changes
        localStorage.setItem("ms-azoaicc:isDarkTheme", JSON.stringify(isDarkTheme));

        // Store isShowingHeader in local storage whenever it changes
        localStorage.setItem("ms-azoaicc:isShowingHeader", JSON.stringify(isShowingHeader));

        // Store customText in local storage whenever it changes
        localStorage.setItem("ms-azoaicc:customText", JSON.stringify(customText));

        // Scroll into view when isLoading changes
        chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" });

        // Toggle 'dark' class on the shell app body element based on the isDarkTheme prop and isConfigPanelOpen
        document.body.classList.toggle("dark", isDarkTheme);
        document.documentElement.dataset.theme = isDarkTheme ? "dark" : "";

        // Clean up the event listener when the component is unmounted
        return () => {
            window.removeEventListener("storage", handleStorageChange);
        };
    }, [customStyles, isBrandingEnabled, isDarkTheme, isLoading, isShowingHeader, customText]);

    const toggleTheme = useCallback((newIsDarkTheme: boolean) => {
        // TODO: chat-component won't exist in the Py demo
        // Get the ChatComponent instance (modify this according to how you manage your components)
        // const chatComponent = document.querySelector("chat-component");

        // if (chatComponent) {
        //     // Remove existing style attributes
        //     chatComponent.removeAttribute("style");
        //     // eslint-disable-next-line unicorn/prefer-dom-node-dataset
        //     chatComponent.setAttribute("data-theme", newIsDarkTheme ? "dark" : "");
        // }

        // Update the body class and html data-theme
        localStorage.removeItem("ms-azoaicc:customStyles");

        // Update the state
        setIsDarkTheme(newIsDarkTheme);
    }, []);

    const setCustomStyle = useCallback((newStyles: CustomStylesState) => {
        setCustomStyles(newStyles);
    }, []);

    const setCustomTexts = useCallback((newText: {}) => {
        setCustomText(newText);
    }, []);

    const enableBranding = useCallback((enabled: boolean) => {
        setEnableBranding(enabled);
    }, []);

    const toggleHeader = useCallback((show: boolean) => {
        setShowHeader(show);
    }, []);

    return (
        <ThemeContext.Provider
            value={{
                /*theme,*/ isDarkTheme,
                isBrandingEnabled,
                isShowingHeader,
                toggleTheme,
                toggleHeader,
                logo,
                chatLogo,
                setCustomStyle,
                setCustomTexts,
                enableBranding,
                customText
            }}
        >
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return context;
};
