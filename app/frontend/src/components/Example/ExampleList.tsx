import { useEffect, useState } from "react";
import { Example } from "./Example";
import { DEFAULT_EXAMPLES, GPT4V_EXAMPLES } from "../../i18n/examples.js";
import styles from "./Example.module.css";
import { setInterval as workerSetInterval, clearInterval as workerClearInterval } from "worker-timers";

interface Props {
    onExampleClicked: (value: string) => void;
    useGPT4V?: boolean;
}

const shuffleArray = (array: string[]) => {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
};

export const ExampleList = ({ onExampleClicked, useGPT4V }: Props) => {
    const [currentExamples, setCurrentExamples] = useState<string[]>([]);

    useEffect(() => {
        const loadExamples = () => {
            const examples = useGPT4V ? GPT4V_EXAMPLES : DEFAULT_EXAMPLES;
            setCurrentExamples(shuffleArray(examples).slice(0, 3));
        };

        loadExamples();
        const intervalId = workerSetInterval(loadExamples, 7000);

        return () => workerClearInterval(intervalId);
    }, [useGPT4V]);

    return (
        <ul className={styles.examplesNavList}>
            {currentExamples.map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
