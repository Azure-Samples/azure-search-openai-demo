import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What funding is available to start a new business in New Zealand?",
    "Tell me more about this assistant.",
    "Who can help me with R&D funding in New Zealand?"
];

const GPT4V_EXAMPLES: string[] = [
    "What funding is available to start a new business in New Zealand?",
    "Tell me more about this assistant.",
    "Who can help me with R&D funding in New Zealand?"
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
