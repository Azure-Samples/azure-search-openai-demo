import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What are the case studies in healthcare domain at virtusa?",
        value: "What are the case studies in healthcare domain at virtusa?"
    },
    { text: "What are Virtusa's solutions on Digital Process Automation using PEGA?", value: "What are Virtusa's solutions on Digital Process Automation using PEGA?" },
    { text: "How can Virtusa help relpace Kony for mobile applications?", value: "How can Virtusa help relpace Kony for mobile applications?" }
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
