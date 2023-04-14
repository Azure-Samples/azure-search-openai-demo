import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Detalii despre LEGEA nr. 144/2022 sub forma de lista",
        value: "Detalii despre LEGEA nr. 144/2022 sub forma de lista"
    },
    { text: "Cum combat in instanta incalcarea articolului 17?", value: "Cum combat in instanta incalcarea articolului 17?" },
    { text: "Diferente intre Art. 27 si Art. 29", value: "Diferente intre Art. 27 si Art. 29" }
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
