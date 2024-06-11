import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What are the policy statements under the Asset Management Policy?",
    "Explain the purpose of the Business Continuity Policy.",
    "What is the process I should follow to log of network devices to maintain network security?"
];

const GPT4V_EXAMPLES: string[] = [
    "What are the policy statements under the Asset Management Policy?",
    "Explain the purpose of the Business Continuity Policy.",
    "What is the process I should follow to log of network devices to maintain network security?"
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
