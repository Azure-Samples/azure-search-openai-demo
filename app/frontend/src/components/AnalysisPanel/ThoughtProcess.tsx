import { Stack } from "@fluentui/react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";

import styles from "./AnalysisPanel.module.css";

import { Thoughts } from "../../api";

SyntaxHighlighter.registerLanguage("json", json);

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
                        <Stack horizontal tokens={{ childrenGap: 5 }}>
                            {t.props &&
                                (Object.keys(t.props) || []).map((k: any) => (
                                    <span className={styles.tProp}>
                                        {k}: {JSON.stringify(t.props?.[k])}
                                    </span>
                                ))}
                        </Stack>
                        {Array.isArray(t.description) ? (
                            <SyntaxHighlighter language="json" wrapLongLines className={styles.tCodeBlock} style={a11yLight}>
                                {JSON.stringify(t.description, null, 2)}
                            </SyntaxHighlighter>
                        ) : (
                            <div>{t.description}</div>
                        )}
                    </li>
                );
            })}
        </ul>
    );
};
