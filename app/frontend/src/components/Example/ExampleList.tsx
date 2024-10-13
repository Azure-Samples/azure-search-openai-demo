import { Example } from "./Example";

import styles from "./Example.module.css";

const Types: string[] = ["Questions", "Features", "Limitations"];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {Types.map((value, i) => (
                <li key={i}>
                    <Example exampleType={value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
