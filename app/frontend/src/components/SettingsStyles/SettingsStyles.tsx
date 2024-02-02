import React, { useState, useEffect } from 'react';
import './SettingsStyles.css';

export type CustomStylesState = {
  AccentHigh: string;
  AccentLight: string;
  AccentDark: string;
  TextColor: string;
  BackgroundColor: string;
  FormBackgroundColor: string;
  BorderRadius: string;
  BorderWidth: string;
  FontBaseSize: string;
};

interface Props {
  onChange: (newStyles: CustomStylesState) => void;
}

export const SettingsStyles = ({ onChange }: Props) => {
  // this needs to come from an API call to some config persisted in the DB
  const styleDefaultsLight = {
    AccentHigh: '#692b61',
    AccentLight: '#f6d5f2',
    AccentDark: '#5e3c7d',
    TextColor: '#123f58',
    BackgroundColor: '#e3e3e3',
    ForegroundColor: '#4e5288',
    FormBackgroundColor: '#f5f5f5',
  };

  const styleDefaultsDark = {
    AccentHigh: '#dcdef8',
    AccentLight: '#032219',
    AccentDark: '#fdfeff',
    TextColor: '#fdfeff',
    BackgroundColor: '#e3e3e3',
    ForegroundColor: '#4e5288',
    FormBackgroundColor: '#32343e',
  };

  const getInitialStyles = (): CustomStylesState => {
    const storedStyles = localStorage.getItem('ms-azoaicc:customStyles');
    const themeStore = localStorage.getItem('ms-azoaicc:isDarkTheme');
    const styleDefaults = themeStore === 'true' ? styleDefaultsDark : styleDefaultsLight;
    if (storedStyles === '') {
      localStorage.setItem('ms-azoaicc:customStyles', JSON.stringify(styleDefaults));
    }
    return storedStyles
      ? JSON.parse(storedStyles)
      : {
          AccentHigh: styleDefaults.AccentHigh,
          AccentLight: styleDefaults.AccentLight,
          AccentDark: styleDefaults.AccentDark,
          TextColor: styleDefaults.TextColor,
          BackgroundColor: styleDefaults.BackgroundColor,
          ForegroundColor: styleDefaults.ForegroundColor,
          FormBackgroundColor: styleDefaults.FormBackgroundColor,
          BorderRadius: '10px',
          BorderWidth: '3px',
          FontBaseSize: '14px',
        };
  };

  const [customStyles, setStyles] = useState<CustomStylesState>(getInitialStyles);

  useEffect(() => {
    // Update the parent component when the state changes
    onChange(customStyles);
  }, [customStyles, onChange]);

  const handleInputChange = (key: keyof CustomStylesState, value: string | number) => {
    setStyles((previousStyles) => ({
      ...previousStyles,
      [key]: value,
    }));
  };

  return (
    <>
      <h3>Modify Styles</h3>
      <div className="ms-style-picker colors">
        {[
          { label: 'Accent High', name: 'AccentHigh', placeholder: 'Accent high' },
          { label: 'Accent Light', name: 'AccentLight', placeholder: 'Accent light' },
          { label: 'Accent Dark', name: 'AccentDark', placeholder: 'Accent dark' },
          { label: 'Text Color', name: 'TextColor', placeholder: 'Text color' },
          { label: 'Background Color', name: 'BackgroundColor', placeholder: 'Background color' },
          { label: 'Foreground Color', name: 'ForegroundColor', placeholder: 'Foreground color' },
          { label: 'Form background', name: 'FormBackgroundColor', placeholder: 'Form Background color' },
        ].map((input) => (
          <React.Fragment key={input.name}>
            <label htmlFor={`accent-${input.name.toLowerCase()}-picker`}>{input.label}</label>
            <input
              name={`accent-${input.name.toLowerCase()}-picker`}
              type="color"
              placeholder={input.placeholder}
              value={customStyles[input.name as keyof CustomStylesState]}
              onChange={(event) => handleInputChange(input.name as keyof CustomStylesState, event.target.value)}
            />
          </React.Fragment>
        ))}
      </div>
      <div className="ms-style-picker sliders">
        {/* Sliders */}
        {[
          { label: 'Border Radius', name: 'BorderRadius', min: 0, max: 25 },
          { label: 'Border Width', name: 'BorderWidth', min: 1, max: 5 },
          { label: 'Font Base Size', name: 'FontBaseSize', min: 12, max: 20 },
        ].map((slider) => (
          <React.Fragment key={slider.name}>
            <div className="ms-settings-input-slider">
              <label htmlFor={`slider-${slider.name.toLowerCase()}`}>{slider.label}</label>
              <input
                name={`slider-${slider.name.toLowerCase()}`}
                type="range"
                min={slider.min}
                max={slider.max}
                placeholder={`Slider for ${slider.name.toLowerCase()}`}
                value={customStyles[slider.name as keyof CustomStylesState]}
                onChange={(event) =>
                  handleInputChange(slider.name as keyof CustomStylesState, `${event.target.value}px`)
                }
              />
              <span className="ms-setting-value">{customStyles[slider.name as keyof CustomStylesState]}</span>
            </div>
          </React.Fragment>
        ))}
      </div>
    </>
  );
};
