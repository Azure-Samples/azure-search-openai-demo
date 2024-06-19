import styles from "./BotType.module.css";

interface Props {
    text: string;
    value: string;
    selected: boolean;
    selectedNumber : number
    onClick: (example: string, id: number) => void;
}

export const BotType = ({ text, value, selected, onClick , selectedNumber }: Props) => {
    return (
        <div className={selected ? styles.example2 : styles.example} onClick={() => onClick(value, selectedNumber)}>
            <p className={styles.exampleText}>{text}</p>
        </div>
    );
};
