import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is difference between Standard Change and Non-Standard Change?",
        value: "What is difference between Standard Change and Non-Standard Change?"
    },
    { text: "what is main purpose of cmdb?", value: "what is main purpose of cmdb?" },
    { text: "What are main activites of Service Delivery Manager?", value: "What are main activites of Service Delivery Manager?" }
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
