import { Stack } from "@fluentui/react";
import SyntaxHighlighter from "react-syntax-highlighter";

import styles from "./AnalysisPanel.module.css";

import { Thoughts } from "../../api";

interface Props {
    thoughts: Thoughts[];
}

export const ThoughtProcess = ({ thoughts }: Props) => {
    return (
        <ul className={styles.tList}>
            {thoughts.map((t, ind) => {
                return (
                    <li className={styles.tListItem} key={ind}>
                        <div className={styles.tStep}>{t.title}</div>
                        {Array.isArray(t.description) ? (
                            <SyntaxHighlighter language="json" wrapLongLines className={styles.tCodeBlock}>
                                {JSON.stringify(t.description, null, 2)}
                            </SyntaxHighlighter>
                        ) : (
                            <>
                                <div>{t.description}</div>
                                <Stack horizontal tokens={{ childrenGap: 5 }}>
                                    {t.props &&
                                        (Object.keys(t.props) || []).map((k: any) => (
                                            <span className={styles.tProp}>
                                                {k}: {JSON.stringify(t.props?.[k])}
                                            </span>
                                        ))}
                                </Stack>
                            </>
                        )}
                    </li>
                );
            })}
        </ul>
    );
};
