import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "How might AI Workflow Optimizer impact team productivity?",
    "What role does AI play in optimizing resource allocation?",
    "How can AI reduce operational costs in manufacturing?"
];

const GPT4V_EXAMPLES: string[] = [
    "How might AI Workflow Optimizer impact team productivity?",
    "What role does AI play in optimizing resource allocation?",
    "How can AI reduce operational costs in manufacturing?"
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
