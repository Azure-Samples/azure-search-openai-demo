import { Delete24Regular } from "@fluentui/react-icons";
import { Button } from "@fluentui/react-components";

import styles from "./SaveChatButton.module.css";
import {DefaultButton} from "@fluentui/react";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const SaveChatButton = ({ className, disabled, onClick }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <DefaultButton
                text={"Save Chat"}
                disabled={disabled}
                onClick={onClick}
            ></DefaultButton>
        </div>
    );
};
