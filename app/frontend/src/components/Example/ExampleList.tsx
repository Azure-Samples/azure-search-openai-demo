import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is frontline negotiation?",
        value: "What is frontline negotiation?"
    },
    { 
        text: "What is the Island of Agreement?", 
        value: "What is the Island of Agreement?" },
    { 
        text: "Why is Island of Agreement important for frontline negotitation?", 
        value: "Why is Island of Agreement important for frontline negotitation?" }
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
