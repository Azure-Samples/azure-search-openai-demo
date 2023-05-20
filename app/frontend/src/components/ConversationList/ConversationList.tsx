import { Conversation } from "./Conversation";
import { ConversationListResponse } from "../../api";
import styles from "./Conversation.module.css";

interface Props {
    listOfConversations: ConversationListResponse | null;
    onConversationClicked: (value: string) => void;
}

export const ConversationList = ({ listOfConversations, onConversationClicked }: Props) => {
    if (!listOfConversations) {
        return null;
    } else {
        return (
            <div className={styles.conversationNavList}>
                {listOfConversations.map(({ id, title, updatedAt, createdAt, userId }, index) => (
                    <Conversation
                        key={index}
                        conversation_id={id}
                        conversation_title={title}
                        userId={userId}
                        updatedAt={updatedAt}
                        createdAt={createdAt}
                        onClick={onConversationClicked}
                    />
                ))}
            </div>
        );
    }
};
