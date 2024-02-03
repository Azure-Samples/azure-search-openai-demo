// src/utils/GlobalStyleManager.ts

/**
 * To implement ..
 * TODO
 */

import { CustomStyles } from "../types";

export class GlobalStyleManager {
    static updateStyleVariable(variableName: string, value: string): void {
        document.documentElement.style.setProperty(variableName, value);
    }

    // static applyCustomStyles(styles: { [key: string]: string }): void {
    static applyCustomStyles(styles: CustomStyles): void {
        Object.entries(styles).forEach(([key, value]) => {
            // Convert camelCase to kebab-case for CSS variable naming
            const cssVariableName = `--${key.replace(/([A-Z])/g, "-$1").toLowerCase()}`;
            GlobalStyleManager.updateStyleVariable(cssVariableName, value);
        });
    }
}
