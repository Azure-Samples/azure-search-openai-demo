import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What are the IT policies of SESA goa?",
    "Give me a brief idea of what is blast furnace?"
];
const EXAMPLES: string[][] = [
    [
        "What are the IT policies of SESA goa?",
        "what are the allowed usage of company laptop?",
        "what are the classification of data privacy level?"
    ],
    [
        "How many leaves I am entitled to?",
        "How to apply for reimbersment?",
        "How many holidays do we get"
    ],
    [
        "How risk assessment is done?",
        "Give me a brief idea of what is blast furnace?"
    ]
];

const GPT4V_EXAMPLES: string[] = [
];

interface Props {
    onExampleClicked: (value: string) => void;
    useGPT4V?: boolean;
    selectedBot:number
}

export const ExampleList = ({ onExampleClicked, useGPT4V , selectedBot}: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {(selectedBot <= 0 ? GPT4V_EXAMPLES : EXAMPLES[selectedBot-1]).map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked}/>
                </li>
            ))}
        </ul>
    );
};
