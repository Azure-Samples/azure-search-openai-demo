import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "How long did it take for Disney+ to reach 100 million subscribers?",
        value: "How long did it take for Disney+ to reach 100 million subscribers?"
    },
    { text: "What is risk based capital requirement?", value: "What is risk based capital requirement?" },
    { text: "Can you explain what is Medicare?", value: "Can you explain what is Medicare?" }
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
