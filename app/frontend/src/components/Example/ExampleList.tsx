import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "How can AI Fusion streamline our current workflow for increased efficiency?",
    "Can VisionAIze help us to predict next quarter's demand patterns?",
    "How can AI reduce operational costs in manufacturing?"
];

const GPT4V_EXAMPLES: string[] = [
    "How can AI Fusion streamline our current workflow for increased efficiency?",
    "Can VisionAIze help us to predict next quarter's demand patterns?",
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
