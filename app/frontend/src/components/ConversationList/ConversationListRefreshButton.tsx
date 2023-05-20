import { Text } from "@fluentui/react";
import { ArrowRepeatAll24Regular } from "@fluentui/react-icons";

import styles from "./ConversationListRefreshButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const ConversationListRefreshButton = ({ className, disabled, onClick }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""} ${disabled && styles.disabled}`} onClick={onClick}>
            <ArrowRepeatAll24Regular />
            <Text>{"Refresh Conversation List"}</Text>
        </div>
    );
};
