import styles from "./Example.module.css";

interface Props {
    text: string;
    value: string;
    contextIndex: string;
    onClick: (value: string, contextIndex: string) => void;
}

export const Example = ({ text, value, contextIndex, onClick }: Props) => {
    return (
        <div className={styles.example} onClick={() => onClick(value, contextIndex)}>
            <p className={styles.exampleText}>{text}</p>
        </div>
    );
};
