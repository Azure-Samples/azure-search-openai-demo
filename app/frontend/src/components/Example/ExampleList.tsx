import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What are low cases involves a knife ?",
        value: "What are low cases involves a knife ?"
    },
    { text: "Please find the cases realted to Urban development ?", value: "Please find the cases realted to Urban development ?" },
    { text: "Any cases related to section 175 of the Criminal Procedure Code ?", value: "Any cases related to section 175 of the Criminal Procedure Code ?" }
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
