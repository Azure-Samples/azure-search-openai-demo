import { Conversation } from "./Conversation";
import { ConversationListResponse } from "../../api";
import styles from "./Conversation.module.css";

interface Props {
    listOfConversations: ConversationListResponse | null;
}

export const ConversationList = ({ listOfConversations }: Props) => {
    console.log("Check out my sexy listOfConversations:", listOfConversations); // Add this line to log the value

    if (!listOfConversations) {
        return null;
    } else {
        return (
            <ul className={styles.examplesNavList}>
                {listOfConversations.map(({ id, title, createdAt, userId }, index) => (
                    <li key={index}>
                        {id}|{title}|{createdAt}|{userId}
                    </li>
                ))}
            </ul>
        );
    }
};
