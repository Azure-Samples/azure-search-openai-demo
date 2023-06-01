import { Conversation } from "./Conversation";
import { ConversationListResponse } from "../../api";
import { ConversationDeleteButton } from "./ConversationDeleteButton";
import { Stack, IStackProps, IStackTokens, Alignment } from "@fluentui/react";
import styles from "./Conversation.module.css";

interface Props {
    listOfConversations: ConversationListResponse | null;
    onConversationClicked: (value: string) => void;
    onDeleteClick: (value: string) => void;
}

export const ConversationList = ({ listOfConversations, onConversationClicked, onDeleteClick }: Props) => {
    if (!listOfConversations) {
        return null;
    } else {
        return (
            <div className={styles.conversationNavList}>
                <Stack verticalAlign="space-between" tokens={{ childrenGap: 5 }}>
                    {listOfConversations.map(({ id, title, updatedAt, createdAt, userId }, index) => (
                        <div key={index}>
                            <Conversation
                                conversation_id={id}
                                conversation_title={title}
                                userId={userId}
                                updatedAt={updatedAt}
                                createdAt={createdAt}
                                onClick={onConversationClicked}
                                onDeleteClick={onDeleteClick}
                            />
                            {/* <ConversationDeleteButton conversation_id={id} className={styles.deleteButton} onClick={onDeleteClick} /> */}
                        </div>
                    ))}
                </Stack>
            </div>
        );
    }
};
