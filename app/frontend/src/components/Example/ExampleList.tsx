import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Highlight a significant project in cloud engineering that you've worked on?",
        value: "Highlight a significant project in cloud engineering that you've worked on?"
    },
    { text: "What inspired your career choice in cloud engineering?", value: "What inspired your career choice in cloud engineering and IT?" },
    { text: "Share an example of successful collaboration with cross-functional teams?", value: "Share an example of successful collaboration with cross-functional teams?" }
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
