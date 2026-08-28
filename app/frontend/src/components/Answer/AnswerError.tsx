import { Stack, PrimaryButton, Icon } from "@fluentui/react";
import styles from "./Answer.module.css";

interface Props {
    error: string;
    onRetry: () => void;
}

export const AnswerError = ({ error, onRetry }: Props) => {
    return (
        <Stack className={styles.answerContainer} verticalAlign="space-between">
            {/* v9 icon-оо v8 MDL2 icon-оор сольж байна */}
            <Icon iconName="ErrorBadge" aria-hidden="true" />

            <Stack.Item grow>
                <p className={styles.answerText}>{error}</p>
            </Stack.Item>

            <PrimaryButton className={styles.retryButton} onClick={onRetry} text="Retry" />
        </Stack>
    );
};
