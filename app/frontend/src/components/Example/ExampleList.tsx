import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "How do I start a new business in New Zealand?",
    "What funding is available for a small business in New Zealand?",
    "What are my responsibilities as a small business owner in New Zealand?"
];

const GPT4V_EXAMPLES: string[] = [
    "How do I start a new business in New Zealand?",
    "What funding is available for a small business in New Zealand?",
    "What are my responsibilities as a small business owner in New Zealand?"
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
