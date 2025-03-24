import type { IRenderFunction } from '@fluentui/utilities';
import styles from "./OptionSlider.module.css";

export interface OptionSliderLabelProps {
    label: string;
    id?: string;
}

export interface OptionSliderProps<T extends string> {
    id?: string;
    value: T;
    label: string;
    options: T[];
    onChange: (value: T) => void;
    defaultValue: T;
    onRenderLabel?: IRenderFunction<OptionSliderLabelProps>;
}

export const OptionSlider = <T extends string>({
    id,
    value,
    label,
    options,
    onChange,
    defaultValue,
    onRenderLabel
}: OptionSliderProps<T>) => {
    // When the provided value is empty (or whitespace only), use the default.
    const normalizedValue = value.trim();
    const displayValue = normalizedValue !== ""
        ? options.find(option => option.toLowerCase() === normalizedValue.toLowerCase()) ?? defaultValue
        : defaultValue;

    // Calculate thumb left position based on the number of options.
    const getThumbLeft = () => {
        const index = options.findIndex(option => option.toLowerCase() === displayValue.toLowerCase());
        return index >= 0 ? index * (100 / options.length) : 0;
    };

    return (
        <div id={id} className={styles.optionSlider}>
            {onRenderLabel
                ? onRenderLabel({ label, id })
                : <label className={styles.sliderLabel}>{label}</label>}            <div className={styles.sliderTrack}>
            <div
                    className={styles.sliderThumb}
                    style={{
                        left: `${getThumbLeft()}%`,
                        width: `${100 / options.length}%`
                    }}
                >
                    {displayValue}
                </div>
                <div className={styles.sliderOptions}>
                    {options.map(option => (
                        <div
                            key={option}
                            className={`${styles.sliderOption} ${option.toLowerCase() === displayValue.toLowerCase() ? "active" : ""}`}
                            onClick={() => onChange(option)}
                        >
                            {option}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};