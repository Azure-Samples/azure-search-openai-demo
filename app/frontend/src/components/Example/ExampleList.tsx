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
    { text: "What is Pfizer's outlook on Covid 19?", value: "what is Pfizer outlook on Covid 19?" },
    { text: "How many female board members in Apple?", value: "How many female board members in Apple?" }
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
