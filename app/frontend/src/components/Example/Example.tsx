import styles from "./Example.module.css";

const Questions: string[] = [
    '"What funding is available to start a new business in New Zealand?"',
    '"Tell me more about this assistant."',
    '"Who can help me with R&D funding in New Zealand?"'
];

const Features: string[] = [
    "Summarised searches from NZ small-business facing ministries and organisations.",
    "Does not record data from your chat.",
    "Multi-lingual. With increasing performance across many labguages of Aotearoa."
];

const Limitations: string[] = [
    "May produce answers that are incorrect, biased, or not referenced in source material.",
    "Limited to only a small number of government web pages and only small business pages, and only small business topics.",
    "Does not provide advice, nor represent the New Zealand government."
];

interface Props {
    exampleType: string;
    onClick: (exampleType: string) => void;
}

export const Example = ({ exampleType, onClick }: Props) => {
    let textList: string[] = [];

    switch (exampleType) {
        case "Questions":
            textList = Questions;
            break;
        case "Features":
            textList = Features;
            break;
        case "Limitations":
            textList = Limitations;
            break;
        default:
            textList = [];
            break;
    }

    return (
        <div className={styles.exampleContainer}>
            <div className={styles.header}>
                <img src="/chatico.png" className={styles.headerImage} />
                <h3>{exampleType}</h3>
            </div>
            {textList.map((text, index) => (
                <div
                    key={index}
                    className={styles.example}
                    onClick={exampleType === "Questions" ? () => onClick(text) : undefined}
                    style={{ cursor: exampleType === "Questions" ? "pointer" : "default" }}
                >
                    <p className={styles.exampleText}>{text}</p>
                </div>
            ))}
        </div>
    );
};
