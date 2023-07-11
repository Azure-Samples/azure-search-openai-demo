import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Is there any information regarding Grupo Bimbo ethics policies?",
        value: "Is there any information regarding Grupo Bimbo ethics policies?"
    },
    { text: "Can you speak other languages?", value: "Can you speak other languages?" },
    { text: "Are you smarter than me?", value: "Are you smarter than me?" }
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
