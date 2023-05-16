import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Wat is de minimale seinafstand tussen een hoofdseinen?",
        value: "Wat is de minimale seinafstand tussen een hoofdseinen?"
    },
    { text: "wat is de minimale zichtbaarheidsafstand?", value: "wat is de minimale zichtbaarheidsafstand?" },
    { text: "Wat weet je over het profiel van vrije ruimte?", value: "Wat weet je over het profiel van vrije ruimte?" }
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
