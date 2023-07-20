import { Text } from "@fluentui/react";

import styles from "./SearchFilterButton.module.css";

interface Props {
    className?: string;
    onClick: () => void;
    disabled?: boolean;
}

export const SearchFilterButton = ({ className, disabled, onClick }: Props) => {
    return (
        <div className={`${styles.container} ${className ?? ""} ${disabled && styles.disabled}`} onClick={onClick}>
            🔎
            <Text>{"Search Filters"}</Text>
        </div>
    );
};
