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
    placeholder?: string;
    onRenderLabel?: IRenderFunction<OptionSliderLabelProps>;
}

export const OptionSlider = <T extends string>({
    id,
    value,
    label,
    options,
    onChange,
    placeholder = "Select an option",
    onRenderLabel
}: OptionSliderProps<T>) => {
    // Calculate thumb left position based on the number of options.
    const getThumbLeft = () => {
        const index = options.findIndex(option => option.toLowerCase() === value.toLowerCase());
        return index >= 0 ? index * (100 / options.length) : 0;
    };

    // Determine displayed text; if value is not in options, display placeholder.
    const displayValue = options.find(option => option.toLowerCase() === value.toLowerCase()) ?? placeholder;

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
                            className={`${styles.sliderOption} ${option.toLowerCase() === value.toLowerCase() ? "active" : ""}`}
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