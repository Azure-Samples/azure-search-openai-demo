import { Text, DefaultButton } from "@fluentui/react";
import styles from "./SearchFilterButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const SearchFilterButton = ({ className, disabled, onClick }: Props) => {
    return (
        <DefaultButton className={`${styles.container} ${className ?? ""} ${disabled && styles.disabled}`} onClick={onClick}>
            🔎
            <Text>{" Search Filters"}</Text>
        </DefaultButton>
    );
};
