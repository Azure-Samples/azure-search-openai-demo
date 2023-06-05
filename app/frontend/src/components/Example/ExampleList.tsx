import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "My patient has a burning feeling in their stomach.",
        value: "My patient has a burning feeling in their stomach."
    },
    { text: "My patient feels pain in their chest when they wake up.", value: "My patient feels pain in their chest when they wake up." },
    { text: "My patient feels pain in front shoulder during overhead movements.", value: "My patient feels pain in front shoulder during overhead movements." }
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
