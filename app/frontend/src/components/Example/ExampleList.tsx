import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is the total number of employees in all industries?",
        value: "What is the total number of employees in all industries?"
    },
    { text: "What is the total number of individuals with work activity during the reference year?", 
      value: "What is the total number of individuals with work activity during the reference year?" },
    { text: "How does employment income vary across different sectors of the North American Industry Classification System (NAICS)?",
      value: "How does employment income vary across different sectors of the North American Industry Classification System (NAICS)?" }
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
