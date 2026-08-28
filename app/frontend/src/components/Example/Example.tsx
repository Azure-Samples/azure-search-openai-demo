import styles from "./Example.module.css";

interface Props {
    text: string;
    value: string;
    icon?: "payment" | "data" | "wallet";
    onClick: (value: string) => void;
}

export const Example = ({ text, value, onClick }: Props) => {
    const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onClick(value);
        }
    };

    return (
        <div className={styles.example} role="button" tabIndex={0} onClick={() => onClick(value)} onKeyDown={handleKeyDown}>
            <p className={styles.exampleText}>{text}</p>
            <span className={styles.exampleArrow} aria-hidden="true">
                →
            </span>
        </div>
    );
};
