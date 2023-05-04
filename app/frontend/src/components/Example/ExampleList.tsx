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
        text: "What is Azure Center for SAP Solutions?",
        value: "What is Azure Center for SAP Solutions?"
    },
    { text: "What are the steps to deploy RHEL PCS Cluster?", value: "What are the steps to deploy RHEL PCS Cluster?" },
    {
        text: "What happen to PP1 system between 1:00 AM and 4:30 AM CST?",
        value: "What happen to PP1 system between 1:00 AM and 4:30 AM CST?"
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
