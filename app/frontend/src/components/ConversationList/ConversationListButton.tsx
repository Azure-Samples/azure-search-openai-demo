import { Text } from "@fluentui/react";
import { BookOpen24Regular } from "@fluentui/react-icons";

import styles from "./ConversationListButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
}

export const ConversationListButton = ({ className, onClick }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""}`} onClick={onClick}>
            <BookOpen24Regular />
            <Text>{"Conversation List"}</Text>
        </div>
    );
};
