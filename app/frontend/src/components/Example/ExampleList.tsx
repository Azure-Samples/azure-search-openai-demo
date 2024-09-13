import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What are the essential procedures for obtaining a license to operate a home healthcare facility in Dubai?",
    "Explain the primary goal of the Clinical Governance Framework outlined by DHA.",
    "What are the key licensure requirements for establishing a dental laboratory that I need to follow?"
];
const GPT4V_EXAMPLES: string[] = [
    "What are the essential procedures for obtaining a license to operate a home healthcare facility in Dubai?",
    "Explain the primary goal of the Clinical Governance Framework outlined by DHA.",
    "What are the key licensure requirements for establishing a dental laboratory that I need to follow?"
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
