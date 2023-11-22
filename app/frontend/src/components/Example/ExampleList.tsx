import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Erzählen Sie mir etwas über den Weinkurs",
        value: "Erzählen Sie mir etwas über den Weinkurs"
    },
    { text: "Wie kommt die Qualität in den Wein?", value: "Wie kommt die Qualität in den Wein?" },
    { text: "Was sind die Die 8 Weinstiltypen?", value: "Was sind die Die 8 Weinstiltypen?" }
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
