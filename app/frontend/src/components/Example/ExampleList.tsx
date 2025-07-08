import { Example } from "./Example";
import { useTranslation } from "react-i18next";

import styles from "./Example.module.css";

interface Props {
    onExampleClicked: (value: string) => void;
    useMultimodalAnswering?: boolean;
}

export const ExampleList = ({ onExampleClicked, useMultimodalAnswering }: Props) => {
    const { t } = useTranslation();

    const DEFAULT_EXAMPLES: string[] = [t("defaultExamples.1"), t("defaultExamples.2"), t("defaultExamples.3")];
    const MULTIMODAL_EXAMPLES: string[] = [t("multimodalExamples.1"), t("multimodalExamples.2"), t("multimodalExamples.3")];

    return (
        <ul className={styles.examplesNavList}>
            {(useMultimodalAnswering ? MULTIMODAL_EXAMPLES : DEFAULT_EXAMPLES).map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
