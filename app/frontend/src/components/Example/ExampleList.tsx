import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What are the responsibilities of the layoff department in managing the SROA program?",
        value: "What are the responsibilities of the layoff department in managing the SROA program?"
    },
    {
        text: "Why might certification lists have more candidates and SROA candidates?",
        value: "Why might certification lists have more candidates and SROA candidates?"
    },
    { text: "How long does surplus status last for an employee?", value: "How long does surplus status last for an employee?" }
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
