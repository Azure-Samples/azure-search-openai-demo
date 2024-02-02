// ThemeSwitch.tsx
import React, { useEffect } from 'react';
import { Toggle } from '@fluentui/react';
import './ThemeSwitch.css';

interface ThemeSwitchProps {
  onToggle: (isDarkTheme: boolean) => void;
  isDarkTheme: boolean;
  isConfigPanelOpen: boolean;
}

export const ThemeSwitch: React.FC<ThemeSwitchProps> = ({ onToggle, isDarkTheme, isConfigPanelOpen }) => {
  const handleToggleChange = () => {
    onToggle(!isDarkTheme); // Pass the new theme state to the parent component
  };

  useEffect(() => {
    // Toggle 'dark' class on the shell app body element based on the isDarkTheme prop and isConfigPanelOpen
    document.body.classList.toggle('dark', isDarkTheme);
    document.documentElement.dataset.theme = isDarkTheme && isConfigPanelOpen ? 'dark' : '';
    localStorage.removeItem('ms-azoaicc:isDarkTheme');
  }, [isDarkTheme, isConfigPanelOpen]);

  return (
    <div className="ms-toggle-wrapper">
      <Toggle
        label="Select theme"
        onText="Dark Theme"
        offText="Light Theme"
        checked={isDarkTheme}
        onChange={handleToggleChange}
      />
    </div>
  );
};
