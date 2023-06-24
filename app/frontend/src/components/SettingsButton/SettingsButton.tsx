import { Text } from "@fluentui/react";
import { Settings28Filled } from "@fluentui/react-icons";

import styles from "./SettingsButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
}

export const SettingsButton = ({ className, onClick }: Props) => {
    return (
        <div className={`${styles.settingsButton} ${className ?? ""}`} onClick={onClick}>
            <Settings28Filled primaryFill="#707070" />
        </div>
    );
};
