import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What is included in my Northwind Health Plus plan that is not in standard?",
        value: "What is included in my Northwind Health Plus plan that is not in standard?"
    },
    { text: "What happens in a performance review?", value: "What happens in a performance review?" },
    { text: "What does a Product Manager do?", value: "What does a Product Manager do?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <div className={styles.examplesContainer}>
            {EXAMPLES.map((x, i) => (
                <Example key={i} text={x.text} value={x.value} onClick={onExampleClicked} />
            ))}
        </div>
    );
};
