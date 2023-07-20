import { Text, DefaultButton } from "@fluentui/react";

import styles from "./CustomerProfileButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const CustomerProfileButton = ({ className, disabled, onClick }: Props) => {
    return (
        <DefaultButton className={`${styles.container} ${className ?? ""} ${disabled && styles.disabled}`} onClick={onClick}>
            🙋‍♂️
            <Text>{" Customer Profile"}</Text>
        </DefaultButton>
    );
};
