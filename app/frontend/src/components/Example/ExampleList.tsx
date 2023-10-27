import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What are perceptions of the flu and its complications, and how has this changed?",
        value: "What are perceptions of the flu and its complications, and how has this changed?"
    },
    {
        text: "What is the best communication channel to deliver the messages to drive uptake of the flu vaccine?",
        value: "What is the best communication channel to deliver the messages to drive uptake of the flu vaccine?"
    },
    {
        text: "What are the drivers and barriers that influence the decision to get vaccinated / recommend vaccination for the COVID and / or Flu? ",
        value: "What are the drivers and barriers that influence the decision to get vaccinated / recommend vaccination for the COVID and / or Flu? "
    }
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
