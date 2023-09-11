import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is the stock price of Microsoft? What is the trend?",
        value: "What is the stock price of Microsoft? What is the trend?"
    },
    { text: "What is Pfizer outlook on Covid 19?", value: "what is Pfizer outlook on Covid 19?" },
    { text: "Can you provide Biographical information of apple?", value: "Can you provide Biographical information of apple?" }
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
