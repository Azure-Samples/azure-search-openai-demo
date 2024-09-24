import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const CHAT_EXAMPLES: ExampleModel[] = [
    {
        text: "What are the top three risks on my project?",
        value: "What are the top three risks on my project?"
    },
    { text: "Who are the stakeholders for the project?", value: "Who are the stakeholders for the project?" },
    { text: "What are the project deliverables?", value: "What are the project deliverables?" }
];
const CREATION_EXAMPLES: ExampleModel[] = [
    { text: "Create a project plan", value: "Create a project plan" },
    { text: "Create a risk assessment document", value: "Create a risk assessment document" },
    { text: "Create a list of deliverables for a project", value: "Create a list of deliverables for a project" }
];
interface Props {
    onExampleClicked: (value: string) => void;
    module: string;
}

export const ExampleList = ({ onExampleClicked, module }: Props) => {
    const examples = module === "Content Creation" ? CREATION_EXAMPLES : CHAT_EXAMPLES;
    return (
        <ul className={styles.examplesNavList}>
            {examples.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
