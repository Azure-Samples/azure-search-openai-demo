import styles from "./BasicCard.module.css";

interface Props {
    title?: string;
    text: string;
}

export const BasicCard = ({ title, text }: Props) => {
    return (
        <div className={styles.basicCard}>
            {title && <p className={styles.basicCardTitle}>{title}</p>}
            <p className={styles.basicCardText}>{text}</p>
        </div>
    );
};
