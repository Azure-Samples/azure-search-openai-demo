import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "What is the definition of Telefónica's purchasing model?",
    "¿Qué compras están excluidas del ámbito MCT?",
    "Quem aprova uma compra igual ou superior a 10.000 euros?"
];

const GPT4V_EXAMPLES: string[] = [
    "What is the definition of Telefónica's purchasing model?",
    "¿Qué compras están excluidas del ámbito MCT?",
    "Quem aprova uma compra igual ou superior a 10.000 euros?"
];

interface Props {
    onExampleClicked: (value: string) => void;
    useGPT4V?: boolean;
}

export const ExampleList = ({ onExampleClicked, useGPT4V }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {(useGPT4V ? GPT4V_EXAMPLES : DEFAULT_EXAMPLES).map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
