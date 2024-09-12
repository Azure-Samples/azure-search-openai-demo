import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What are the major types of genetic mutations that can lead to the development of diseases?",
    "How has the COVID-19 pandemic accelerated healthcare innovation and improved management protocols for respiratory diseases?",
    "What are the primary differences between antigenic drift and antigenic shift in influenza viruses?"
];

const GPT4V_EXAMPLES: string[] = [
    "What are the major types of genetic mutations that can lead to the development of diseases?",
    "How has the COVID-19 pandemic accelerated healthcare innovation and improved management protocols for respiratory diseases?",
    "What are the primary differences between antigenic drift and antigenic shift in influenza viruses?"
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
