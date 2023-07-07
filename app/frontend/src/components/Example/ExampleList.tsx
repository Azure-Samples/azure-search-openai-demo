import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What automation features are available in OneCloud V1 Release?",
        value: "What automation features are available in OneCloud V1 Release?"
    },
    { text: "What are the most used automation usecase listed in the automation library?", value: "What are the most used automation usecase listed in the automation library?" },
    { text: "What is the role of a deployment lead?", value: "What is the role of a deployment lead?" }
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
