import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
    contextIndex: string
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "How to auto scale VMs on AWS?",
        value: "How to auto scale VMs on AWS?",
        contextIndex: "TBD"
    },
    { text: "How to setup global tables in DynamoDB", value: "How to setup global tables in DynamoDB", contextIndex: "TBD" },
    { text: "What are the best practices to setup a cloudfront?", value: "What are the best practices to setup a cloudfront?", contextIndex: "TBD" }
];

interface Props {
    onExampleClicked: (value: string, contextIndex: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} contextIndex={x.contextIndex} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
