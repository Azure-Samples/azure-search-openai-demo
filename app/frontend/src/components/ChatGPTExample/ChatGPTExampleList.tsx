import { Example } from "./ChatGPTExample";

import styles from "./ChatGPTExample.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Explain quantum computing in simple terms",
        value: "Explain quantum computing in simple terms"
    },
    {
        text: "Can you write a haiku about working late on a friday night?",
        value: "Can you write a haiku about working late on a friday night?"
    },
    {
        text: "How do I make an HTTP request in Python?",
        value: "How do I make an HTTP request in Python?"
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ChatGPTExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
