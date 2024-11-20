import styles from "./Example.module.css";

const Questions: string[] = [
    '"What funding and support is available for NZ businesses?"',
    '"What is the System Prompt for this assistant?"',
    '"Tell me more about this assistant."'
];

const Features: string[] = [
    "Summarised searches from NZ small-business facing ministries and organisations.",
    "Does not record data from your chat.",
    "Multi-lingual. Reo Maha. Gagana e Tele. Lea Lahi."
];

const Limitations: string[] = [
    "May produce answers that are incorrect, biased, or not referenced in source material.",
    "Limited to only a small number of government web pages and only small business pages, and only small business topics.",
    "Does not provide advice, nor represent the New Zealand government."
];

interface Props {
    exampleType: string;
    onClick: (question: string) => void;
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
                <img src="/icon.png" className={styles.headerImage} />
                <h3>{exampleType}</h3>
            </div>
            {textList.map((text, index) => {
                const isQuestion = exampleType === "Questions";

                // Determine if the text contains the word "web pages" (case-insensitive)
                const containsWeb = /web pages/i.test(text);

                const containerClassName = isQuestion ? styles.exampleQuestion : styles.exampleOther;

                const containerStyle = { cursor: isQuestion ? "pointer" : "default" };
                const onClickHandler = isQuestion ? () => onClick(text) : undefined;

                // Process the text to include a hyperlink if it contains "web pages"
                let content;
                if (containsWeb) {
                    const parts = text.split(/(web pages)/i);
                    content = (
                        <p className={styles.exampleText}>
                            {parts.map((part, i) => {
                                if (part.toLowerCase() === "web pages") {
                                    return (
                                        <a key={i} href="https://ai-activator.circle.so/c/govchat-faq/indexed-sites" target="_blank" rel="noopener noreferrer">
                                            {part}
                                        </a>
                                    );
                                } else {
                                    return part;
                                }
                            })}
                        </p>
                    );
                } else {
                    content = <p className={styles.exampleText}>{text}</p>;
                }

                return (
                    <div key={index} className={containerClassName} onClick={onClickHandler} style={containerStyle}>
                        {content}
                    </div>
                );
            })}
        </div>
    );
};
