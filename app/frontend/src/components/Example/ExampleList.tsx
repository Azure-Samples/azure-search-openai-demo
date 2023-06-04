import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Show me data for Commercial Banking Payments testing.",
        value: "Show me data for Commercial Banking Payments testing."
    },
    { text: "Get me all case studies that leverages Kanban and in Retail banking.", value: "Get me all case studies that leverages Kanban and in Retail banking." },
    { text: "What are the case studies in healthcare domain at virtusa?", value: "What are the case studies in healthcare domain at virtusa?" }
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
