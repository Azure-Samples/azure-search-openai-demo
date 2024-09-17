import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "How to improve quality of farm soil specifically for cultivating corn?",
    "What are the benefits of using zinc seed treatments for corn cultivation?",
    "What factors should be considered for optimal Soybean cultivation?"
];

const GPT4V_EXAMPLES: string[] = [
    "How to improve quality of farm soil specifically for cultivating corn?",
    "What are the benefits of using zinc seed treatments for corn cultivation?",
    "What factors should be considered for optimal Soybean cultivation?"
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
