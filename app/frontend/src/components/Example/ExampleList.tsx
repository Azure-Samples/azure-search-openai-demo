import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What is included in my Northwind Health Plus plan that is not in standard?",
    "What happens in a performance review?",
    "What does a Product Manager do?"
];

const GPT4V_EXAMPLES: string[] = [
    "Compare the impact of interest rates and GDP in financial markets.",
    "What is the expected trend for the S&P 500 index over the next five years? Compare it to the past S&P 500 performance",
    "Can you identify any correlation between oil prices and stock market trends?"
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
