import styles from "./Conversation.module.css";

interface Props {
    conversation_id: string;
    conversation_title: string;
    userId: string;
    updatedAt: string;
    createdAt: string;
    onClick: (value: string) => void;
}

export const Conversation = ({ conversation_id, conversation_title, createdAt, updatedAt, userId, onClick }: Props) => {
    //check if the conversation title is undefined
    if (conversation_title === "") {
        conversation_title = "New Conversation";
    }

    const createdDate = new Date(Date.parse(updatedAt));
    const dateOptions = {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true
    } as Intl.DateTimeFormatOptions;

    return (
        <div className={styles.conversation} onClick={() => onClick(conversation_id)}>
            <h2 className={styles.conversationHeader}>{conversation_title}</h2>
            <p className={styles.conversationText}>Last Updated: {createdDate.toLocaleString("en-US", dateOptions)}</p>
        </div>
    );
};
