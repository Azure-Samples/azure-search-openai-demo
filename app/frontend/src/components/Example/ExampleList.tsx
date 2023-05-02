import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        //   text: "What is included in my Northwind Health Plus plan that is not in standard?",
        //  value: "What is included in my Northwind Health Plus plan that is not in standard?"
        text: "What are supported Azure VM SKUs with 2TB memory for SAP HANA?",
        value: "What are supported Azure VM SKUs with 2TB memory for SAP HANA?"
    },
    { text: "How do I deploy SAP S/4 HANA system in HA configuration?", value: "How do I deploy SAP S/4 HANA system in HA configuration" },
    {
        text: "Future: What happen to SP1 system last night between 1:00AM and 4AM system time?",
        value: "Future: What happen to SP1 system last night between 1:00AM and 4AM system time?"
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
