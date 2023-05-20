import styles from "./Conversation.module.css";

interface Props {
    text: string;
    value: string;
    onClick: (value: string) => void;
}

export const Conversation = ({ text, value, onClick }: Props) => {
    return (
        <div className={styles.conversation} onClick={() => onClick(value)}>
            <p className={styles.conversationText}>{text}</p>
        </div>
    );
};
