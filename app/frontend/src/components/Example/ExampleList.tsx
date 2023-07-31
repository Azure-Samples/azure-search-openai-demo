import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What are the waiting periods for our corporate hospital covers?",
        value: "What are the waiting periods for our corporate hospital covers?"
    },
    {
        text: "How many months do I have to wait before I can avail the services included in Gold Ultimate Health cover?",
        value: "How many months do I have to wait before I can avail the services included in Gold Ultimate Health cover?"
    },
    { text: "How can you help me?", value: "How can you help me?" }
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
