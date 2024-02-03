import React, { useState, useEffect } from "react";
import "./SettingsStyles.css";
import { CustomStyles } from "../../types";

interface Props {
    onChange: (newStyles: CustomStyles) => void;
}

const SettingsStyles: React.FC<Props> = React.memo(({ onChange }) => {
    const styleDefaultsLight: CustomStyles = {
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

    const styleDefaultsDark: CustomStyles = {
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

    const getInitialStyles = (): CustomStyles => {
        const storedStyles = localStorage.getItem("ms-azoaicc:customStyles");
        const themeStore = localStorage.getItem("ms-azoaicc:isDarkTheme");
        const styleDefaults = themeStore === "true" ? styleDefaultsDark : styleDefaultsLight;
        return storedStyles ? JSON.parse(storedStyles) : { ...styleDefaults };
    };

    const [customStyles, setStyles] = useState<CustomStyles>(getInitialStyles);

    useEffect(() => {
        onChange(customStyles);
    }, [customStyles, onChange]);

    const handleInputChange = (key: keyof CustomStyles, value: string) => {
        setStyles(previousStyles => ({
            ...previousStyles,
            [key]: value
        }));
    };

    return (
        <>
            <h3>Modify Styles</h3>
            <div className="ms-style-picker colors">
                {[
                    { label: "Accent High", name: "AccentHigh" },
                    { label: "Accent Light", name: "AccentLight" },
                    { label: "Accent Dark", name: "AccentDark" },
                    { label: "Text Color", name: "TextColor" },
                    { label: "Background Color", name: "BackgroundColor" },
                    { label: "Foreground Color", name: "ForegroundColor" },
                    { label: "Form Background", name: "FormBackgroundColor" }
                ].map(({ label, name }) => (
                    <div key={name}>
                        <label htmlFor={`accent-${name}-picker`}>{label}</label>
                        <input
                            id={`accent-${name}-picker`}
                            type="color"
                            value={customStyles[name as keyof CustomStyles]}
                            onChange={event => handleInputChange(name as keyof CustomStyles, event.target.value)}
                        />
                    </div>
                ))}
            </div>
            <div className="ms-style-picker sliders">
                {[
                    { label: "Border Radius", name: "BorderRadius", min: 0, max: 25 },
                    { label: "Border Width", name: "BorderWidth", min: 1, max: 5 },
                    { label: "Font Base Size", name: "FontBaseSize", min: 12, max: 20 }
                ].map(({ label, name, min, max }) => (
                    <div key={name} className="ms-settings-input-slider">
                        <label htmlFor={`slider-${name}`}>{label}</label>
                        <input
                            id={`slider-${name}`}
                            type="range"
                            min={min}
                            max={max}
                            value={parseInt(customStyles[name as keyof CustomStyles])}
                            onChange={event => handleInputChange(name as keyof CustomStyles, `${event.target.value}px`)}
                        />
                        <span className="ms-setting-value">{customStyles[name as keyof CustomStyles]}</span>
                    </div>
                ))}
            </div>
        </>
    );
});

export default SettingsStyles;
