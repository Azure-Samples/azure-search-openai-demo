import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Give me a detailed executive summary of APEX. Give it to me in a way that a credit analyst at hedge fund would want to know. Provide sources.",
        value: "Give me a detailed executive summary of APEX. Give it to me in a way that a credit analyst at hedge fund would want to know. Provide sources."
    },
    { text: "What are the positive and negative trends about Apex Tool?", value: "What are the positive and negative trends about Apex Tool?" },
    { text: "What's the latest data available for Apex Tool?", value: "What's the latest data available for Apex Tool?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
