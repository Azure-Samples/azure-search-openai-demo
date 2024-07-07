import { Stack } from "@fluentui/react";
import { animated, useSpring } from "@react-spring/web";
import { useTranslation } from "react-i18next";

import styles from "./Answer.module.css";
import { AnswerIcon } from "./AnswerIcon";

export const AnswerLoading = () => {
    const { t, i18n } = useTranslation();
    const animatedStyles = useSpring({
        from: { opacity: 0 },
        to: { opacity: 1 }
    });

    return (
        <animated.div style={{ ...animatedStyles }}>
            <Stack className={styles.answerContainer} verticalAlign="space-between">
                <AnswerIcon />
                <Stack.Item grow>
                    <p className={styles.answerText}>
                        {t("generatingAnswer")}
                        <span className={styles.loadingdots} />
                    </p>
                </Stack.Item>
            </Stack>
        </animated.div>
    );
};
