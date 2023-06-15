import { Example } from "./Example";
import { useEffect } from "react";
import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Hello!",
        value: ""
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    useEffect(() => {
        if (EXAMPLES.length > 0) {
            const firstExample = EXAMPLES[0];
            onExampleClicked(firstExample.value);
        }
    }, []);

    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={""} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
