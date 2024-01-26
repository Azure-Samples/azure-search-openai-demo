import { Book24Regular, Delete24Regular } from "@fluentui/react-icons";
import { Button } from "@fluentui/react-components";

import styles from "./SourceListButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const SourceListButton = ({ className, disabled, onClick }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <Button icon={<Book24Regular />} disabled={disabled} onClick={onClick}>
                {"List Sources"}
            </Button>
        </div>
    );
};
