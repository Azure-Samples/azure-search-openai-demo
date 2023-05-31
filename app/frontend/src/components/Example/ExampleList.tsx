import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "TDG 연혁에 대해서 알려주세요",
        value: "TDG 연혁에 대해서 알려주세요"
    },
    { text: "TDG 입사시 필요한 내용은?", value: "TDG 입사시 필요한 내용은?" },
    { text: "TDG 복지는 어떤게 있나요?", value: "TDG 복지는 어떤게 있나요?" }
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
