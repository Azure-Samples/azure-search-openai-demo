import { Delete20Regular } from "@fluentui/react-icons";

import styles from "./ConversationDeleteButton.module.css";

interface Props {
    conversation_id: string;
    className?: string;
    onClick: (value: string) => void;
}

export const ConversationDeleteButton = ({ conversation_id, className, onClick }: Props) => {
    // todo: add accessble tags for delete button
    return (
        <div className={`${styles.container} ${className ?? ""}`} onClick={() => onClick(conversation_id)}>
            <Delete20Regular />
        </div>
    );
};
