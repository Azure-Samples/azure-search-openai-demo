import { Text, DefaultButton } from "@fluentui/react";
import { Settings24Regular } from "@fluentui/react-icons";

import styles from "./SettingsButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
}

export const SettingsButton = ({ className, onClick }: Props) => {
    return (
        <DefaultButton className={`${styles.container} ${className ?? ""}`} onClick={onClick}>
            <Settings24Regular />
            <Text>{" Assistant settings"}</Text>
        </DefaultButton>
    );
};
