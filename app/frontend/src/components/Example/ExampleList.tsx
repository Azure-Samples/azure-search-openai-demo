import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Miten toimia kaukolämpövikailmoitusten kanssa?",
        value: "Miten toimia kaukolämpövikailmoitusten kanssa?"
    },
    { text: "Mikä on virtuaaliakku?", value: "Mikä on virtuaaliakku?" },
    { text: "Miten kirjoitetaan salattu viesti?", value: "Miten kirjoitetaan salattu viesti?" }
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
