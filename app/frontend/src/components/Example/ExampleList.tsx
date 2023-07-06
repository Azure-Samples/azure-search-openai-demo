import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is a Hospital at Home?",
        value: "What is a Hospital at Home?"
    },
    { text: "What is the confidence in the Healthcare system in 2022?", value: "What is the confidence in the Healthcare system in 2022?" },
    { text: "Describe Intensive Transitional Care Management Intervention", value: "Describe Intensive Transitional Care Management Intervention" }
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
