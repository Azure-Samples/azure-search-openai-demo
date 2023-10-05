import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What are the latest news regarding implants?",
        value: "What are the latest news regarding implants?"
    },
    {
        text: "Are there any new technologies or methodologies that are gaining traction?",
        value: "Are there any new technologies or methodologies that are gaining traction?"
    },
    {
        text: "Are there any new product launches, partnerships, or expansions by competitors?",
        value: "Are there any new product launches, partnerships, or expansions by competitors?"
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
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
