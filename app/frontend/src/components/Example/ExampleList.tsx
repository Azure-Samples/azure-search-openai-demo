import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What was Brookfield revenue in 2022?",
        value: "What was Brookfield revenue in 2022?"
    },
    { text: "What was Brookfield revenue in 2023?", value: "What was Brookfield revenue in 2023?" },
    { text: "what is brookfield investment apporach?", value: "what is brookfield investment apporach?" }
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
