import { ConversationDeleteButton } from "./ConversationDeleteButton";
import styles from "./Conversation.module.css";
import { Stack, IStackProps, IStackTokens, Alignment } from "@fluentui/react";

interface Props {
    conversation_id: string;
    conversation_title: string;
    userId: string;
    updatedAt: string;
    createdAt: string;
    onClick: (value: string) => void;
    onDeleteClick: (value: string) => void;
}

export const Conversation = ({ conversation_id, conversation_title, createdAt, updatedAt, userId, onClick, onDeleteClick }: Props) => {
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
            <Stack horizontal horizontalAlign="space-between" tokens={{ childrenGap: 30 }}>
                <div className={styles.conversationWrapper} key={conversation_id + "inner_div"}>
                    <h2 className={styles.conversationHeader}>{conversation_title}</h2>
                    <p className={styles.conversationText}>Last Updated: {createdDate.toLocaleString("en-US", dateOptions)}</p>
                </div>
                <ConversationDeleteButton conversation_id={conversation_id} className={styles.deleteButton} onClick={onDeleteClick} />
            </Stack>
        </div>
    );
};
