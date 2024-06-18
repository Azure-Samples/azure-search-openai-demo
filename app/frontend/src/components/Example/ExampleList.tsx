import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "Explain the Car Capital funding process in detail.",
    "What happens in a buyback scenario?",
    "What are some good tips for ASMs when making sales calls on dealers?"
];

const GPT4V_EXAMPLES: string[] = [
    "Explain what a buyback is and how the process works.",
    "What documentation is required to be submitted by the dealer and reviewed by CCT prior to funding?",
    "What information needs to be verified before any application is funded?"
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
