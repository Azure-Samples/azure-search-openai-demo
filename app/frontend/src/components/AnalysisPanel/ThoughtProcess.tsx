import { Stack } from "@fluentui/react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";

import styles from "./AnalysisPanel.module.css";

import { Thoughts } from "../../api";
import { TokenUsageGraph } from "./TokenUsageGraph";
import { Evaluation } from "./Evaluation";
import { Reflection } from "./Reflection";
import { CandidateAnswer } from "./CandidateAnswer";

SyntaxHighlighter.registerLanguage("json", json);

interface Props {
    thoughts: Thoughts[];
}

const known_keys = ["token_usage", "reasoning_effort", "groundedness", "relevance", "correctness", "next_query", "next_answer", "candidate_answer"];

export const ThoughtProcess = ({ thoughts }: Props) => {
    return (
        <ul className={styles.tList}>
            {thoughts.map((t, ind) => {
                return (
                    <li className={styles.tListItem} key={ind}>
                        <div className={styles.tStep}>{t.title}</div>
                        <Stack horizontal tokens={{ childrenGap: 5 }}>
                            {t.props &&
                                (Object.keys(t.props).filter(k => !known_keys.includes(k)) || []).map((k: any) => (
                                    <span className={styles.tProp} key={k}>
                                        {k}: {JSON.stringify(t.props?.[k])}
                                    </span>
                                ))}
                        </Stack>
                        {t.props?.token_usage && <TokenUsageGraph tokenUsage={t.props.token_usage} reasoningEffort={t.props.reasoning_effort} />}

                        {Array.isArray(t.description) ? (
                            <SyntaxHighlighter language="json" wrapLongLines className={styles.tCodeBlock} style={a11yLight}>
                                {JSON.stringify(t.description, null, 2)}
                            </SyntaxHighlighter>
                        ) : (
                            <div>{t.description}</div>
                        )}

                        {t.props?.groundedness && <Evaluation label="Groundedness" value={t.props.groundedness} />}
                        {t.props?.relevance && <Evaluation label="Relevance" value={t.props.relevance} />}
                        {t.props?.correctness && <Evaluation label="Correctness" value={t.props.correctness} />}
                        {(t.props?.next_query || t.props?.next_answer) && <Reflection next_query={t.props.next_query} next_answer={t.props.next_answer} />}
                        {t.props?.candidate_answer && <CandidateAnswer candidate_answer={t.props.candidate_answer} />}
                    </li>
                );
            })}
        </ul>
    );
};
