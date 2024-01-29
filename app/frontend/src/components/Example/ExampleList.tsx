import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What does the law specify regarding hygiene at the office?",
    "How should mental wellbeing of the employees be respected?",
    "What should one do in case of a work accident?"
];

const GPT4V_EXAMPLES: string[] = [
    "What does the law specify regarding hygiene at the office?",
    "How should mental wellbeing of the employees be respected?",
    "What should one do in case of a work accident?"
];

interface Props {
    onExampleClicked: (value: string) => void;
    useGPT4V?: boolean;
}

export const ExampleList = ({ onExampleClicked, useGPT4V }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {(useGPT4V ? GPT4V_EXAMPLES : DEFAULT_EXAMPLES).map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
