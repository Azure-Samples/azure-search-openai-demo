import styles from "./Example.module.css";

const Questions: string[] = [
    '"What are the expected progress outcomes by the end of Year 6?"',
    '"Please outline the teaching sequence for years 4-6."',
    '"How should texts be selected for reading in years 4-6?"'
];

const Features: string[] = [
    "Summarised searches from the Ministry of Education Curriculum (Tāhūrangi), NZC - English (Phase 2) web site.",
    "Does not record data from your chat.",
    "Multi-lingual. Reo Maha. Gagana e Tele. Lea Lahi."
];

const Limitations: string[] = [
    "May produce answers that are incorrect, biased, or not referenced in source material.",
    "Limited to only the Ministry of Education Curriculum (Tāhūrangi), NZC - English (Phase 2) web site.",
    "Does not provide advice, nor represent the Ministry of Education."
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
