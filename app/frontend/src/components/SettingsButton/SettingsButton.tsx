import { Settings24Regular } from "@fluentui/react-icons";
import { Button } from "@fluentui/react-components";

import styles from "./SettingsButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
}

export const SettingsButton = ({ className, onClick }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""}`}>
            <Button icon={<Settings24Regular />} onClick={onClick}>
                {"Developer settings"}
            </Button>
        </div>
    );
};
