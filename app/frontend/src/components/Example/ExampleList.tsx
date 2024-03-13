import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "Comment accéder à mon planning mensuel ?",
    "Puis-je modifier les couleurs de mon planning?",
    "Est ce que Octime recrute actuellement ?"
];

const GPT4V_EXAMPLES: string[] = [
    "Peux-tu me montrer à quoi ressemble le module alerteur ?",
    "Montre moi l'écran des remplacements stp",
    "Est-ce que je peux paramétrer du SSO pour l'accès à Octime?"
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
