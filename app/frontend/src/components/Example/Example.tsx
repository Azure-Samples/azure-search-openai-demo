import styles from "./Example.module.css";

interface Props {
    text: string;
    value: string;
    bgColor: string;
    onClick: (value: string) => void;
}

export const Example = ({ text, value, bgColor, onClick }: Props) => {
    return (
        <div className={styles.example} onClick={() => onClick(value)} style={{ backgroundColor: bgColor }}>
            <p className={styles.exampleText}>{text}</p>
        </div>
    );
};
