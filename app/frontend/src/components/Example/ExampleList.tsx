import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What's the business model of Apex Tool?",
        value: "What's the business model of Apex Tool?"
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
